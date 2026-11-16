from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.utils.dateparse import parse_date
from accounts.decorators import role_required
from sales.models import CustomerFeedback, DeliveryRecord, SalesOrder, PaymentRecord

manager_required = role_required('super_admin','institution_admin','manager')

def _global_admin(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(
        profile and profile.is_active and profile.role in ("super_admin", "institution_admin")
    )


def _visible_orders(user):
    qs = SalesOrder.objects.select_related("customer", "responsible_staff__department")
    if _global_admin(user):
        return qs
    profile = getattr(user, "profile", None)
    department_id = profile.department_id if profile and profile.role == "manager" else None
    return qs.filter(customer__department_id=department_id) if department_id else qs.none()


def _visible_deliveries(user):
    return DeliveryRecord.objects.filter(order__in=_visible_orders(user))


def _delivery(d):
    return {'id': d.id, 'order_id': d.order_id, 'order_no': d.order.order_no, 'customer': d.order.customer.name,
            'delivery_date': d.delivery_date.isoformat() if d.delivery_date else '', 'address': d.address,
            'transport': d.transport, 'responsible_person': d.responsible_person, 'installation_required': d.installation_required,
            'installation_date': d.installation_date.isoformat() if d.installation_date else '', 'status': d.status,
            'status_label': d.get_status_display(), 'acknowledgement': d.acknowledgement, 'completion_notes': d.completion_notes}

@login_required
@manager_required
@require_GET
def summary(request):
    q=request.GET.get('q','').strip()
    qs=_visible_deliveries(request.user).select_related('order__customer')
    if q: qs=qs.filter(Q(order__order_no__icontains=q)|Q(order__customer__name__icontains=q))
    return JsonResponse({'stats': {
        'pending': qs.filter(status='pending').count(),
        'scheduled': qs.filter(status='scheduled').count(),
        'out': qs.filter(status='out').count(),
        'delivered': qs.filter(status__in=['delivered','installed']).count(),
        'installations': qs.filter(installation_required=True,status__in=['scheduled','out']).count(),
    }, 'deliveries': [_delivery(x) for x in qs[:100]]})

@login_required
@manager_required
@require_GET
def detail(request, pk):
    order=get_object_or_404(_visible_orders(request.user), pk=pk)
    d,_=DeliveryRecord.objects.get_or_create(order=order)
    fb=CustomerFeedback.objects.filter(order=order).first()
    data=_delivery(d); data['feedback']={'rating': fb.rating if fb else '', 'comment': fb.comment if fb else ''}
    return JsonResponse(data)

@login_required
@manager_required
@require_POST
@transaction.atomic
def update(request, pk):
    import json
    try:
        data = json.loads(request.body or '{}')
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)
    order = get_object_or_404(_visible_orders(request.user).select_for_update(of=("self",)), pk=pk)
    d = DeliveryRecord.objects.select_for_update().filter(order=order).first()
    current_status = d.status if d else DeliveryRecord.Status.PENDING
    if d is None:
        d = DeliveryRecord(order=order)

    date_fields = ('delivery_date', 'installation_date')
    for field in date_fields:
        if field in data:
            raw = data[field]
            try:
                parsed = parse_date(raw) if raw else None
            except (TypeError, ValueError):
                parsed = None
            if raw and parsed is None:
                return JsonResponse({'detail': f'Invalid {field.replace("_", " ")}.'}, status=400)
            setattr(d, field, parsed)

    text_fields = ('address', 'transport', 'responsible_person', 'acknowledgement', 'completion_notes')
    for field in text_fields:
        if field in data:
            setattr(d, field, str(data[field] or ''))

    if 'installation_required' in data:
        if not isinstance(data['installation_required'], bool):
            return JsonResponse({'detail': 'installation_required must be true or false.'}, status=400)
        d.installation_required = data['installation_required']

    if 'status' in data:
        requested = data['status']
        valid_statuses = {value for value, _ in DeliveryRecord.Status.choices}
        if not isinstance(requested, str) or requested not in valid_statuses:
            return JsonResponse({'detail': 'Invalid delivery status.'}, status=400)
        transitions = {
            DeliveryRecord.Status.PENDING: {DeliveryRecord.Status.PENDING, DeliveryRecord.Status.SCHEDULED, DeliveryRecord.Status.CANCELLED},
            DeliveryRecord.Status.SCHEDULED: {DeliveryRecord.Status.SCHEDULED, DeliveryRecord.Status.READY, DeliveryRecord.Status.OUT, DeliveryRecord.Status.CANCELLED},
            DeliveryRecord.Status.READY: {DeliveryRecord.Status.READY, DeliveryRecord.Status.OUT, DeliveryRecord.Status.CANCELLED},
            DeliveryRecord.Status.OUT: {DeliveryRecord.Status.OUT, DeliveryRecord.Status.DELIVERED, DeliveryRecord.Status.INSTALLED, DeliveryRecord.Status.CANCELLED},
            DeliveryRecord.Status.DELIVERED: {DeliveryRecord.Status.DELIVERED, DeliveryRecord.Status.INSTALLED},
            DeliveryRecord.Status.INSTALLED: {DeliveryRecord.Status.INSTALLED},
            DeliveryRecord.Status.CANCELLED: {DeliveryRecord.Status.CANCELLED},
        }
        if requested not in transitions[current_status]:
            return JsonResponse({'detail': 'This delivery status transition is not allowed.'}, status=400)
        if requested in (DeliveryRecord.Status.READY, DeliveryRecord.Status.OUT, DeliveryRecord.Status.DELIVERED, DeliveryRecord.Status.INSTALLED) and order.status not in (SalesOrder.Status.READY, SalesOrder.Status.DELIVERED):
            return JsonResponse({'detail': 'The Sales Order must pass Final QC and be marked Ready before delivery can proceed.'}, status=400)
        if requested in (DeliveryRecord.Status.OUT, DeliveryRecord.Status.DELIVERED, DeliveryRecord.Status.INSTALLED):
            paid_total = order.payments.filter(
                status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED]
            ).aggregate(total=Sum("amount"))["total"] or 0
            if paid_total < order.confirmed_price and not order.credit_exception_approved_by_id:
                return JsonResponse({
                    "detail": "Final payment must be received before dispatch unless a Founder-approved credit exception is recorded.",
                    "order_total": str(order.confirmed_price),
                    "paid_total": str(paid_total),
                    "balance": str(order.confirmed_price - paid_total),
                }, status=400)
        if requested == DeliveryRecord.Status.INSTALLED and not d.installation_required:
            return JsonResponse({'detail': 'Installation must be marked as required before an order can be marked Installed.'}, status=400)
        d.status = requested

    d.save()
    if d.status in (DeliveryRecord.Status.DELIVERED, DeliveryRecord.Status.INSTALLED):
        if order.status != SalesOrder.Status.DELIVERED:
            order.status = SalesOrder.Status.DELIVERED
            order.save(update_fields=['status', 'updated_at'])
    return JsonResponse(_delivery(d))

@login_required
@manager_required
@require_POST
def feedback(request, pk):
    import json
    try:
        data=json.loads(request.body or '{}')
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)
    order=get_object_or_404(_visible_orders(request.user), pk=pk)
    if order.status != SalesOrder.Status.DELIVERED:
        return JsonResponse({'detail': 'Customer feedback can be recorded only after the order is delivered.'}, status=400)
    raw_rating=data.get('rating')
    try:
        rating=int(raw_rating) if raw_rating not in (None, '') else None
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'Rating must be an integer from 1 to 5.'}, status=400)
    if rating is not None and not 1 <= rating <= 5:
        return JsonResponse({'detail': 'Rating must be between 1 and 5.'}, status=400)
    fb,_=CustomerFeedback.objects.get_or_create(order=order)
    fb.rating=rating; fb.comment=str(data.get('comment','') or '')[:5000]; fb.save()
    return JsonResponse({'rating':fb.rating,'comment':fb.comment})
