from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from accounts.decorators import role_required
from sales.models import CustomerFeedback, DeliveryRecord, SalesOrder

manager_required = role_required('super_admin','institution_admin','manager')

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
    qs=DeliveryRecord.objects.select_related('order__customer').all()
    if q: qs=qs.filter(Q(order__order_no__icontains=q)|Q(order__customer__name__icontains=q))
    return JsonResponse({'stats': {'pending': DeliveryRecord.objects.filter(status='pending').count(), 'scheduled': DeliveryRecord.objects.filter(status='scheduled').count(), 'out': DeliveryRecord.objects.filter(status='out').count(), 'delivered': DeliveryRecord.objects.filter(status__in=['delivered','installed']).count(), 'installations': DeliveryRecord.objects.filter(installation_required=True,status__in=['scheduled','out']).count()}, 'deliveries': [_delivery(x) for x in qs[:100]]})

@login_required
@manager_required
@require_GET
def detail(request, pk):
    order=SalesOrder.objects.select_related('customer').get(pk=pk)
    d,_=DeliveryRecord.objects.get_or_create(order=order)
    fb=CustomerFeedback.objects.filter(order=order).first()
    data=_delivery(d); data['feedback']={'rating': fb.rating if fb else '', 'comment': fb.comment if fb else ''}
    return JsonResponse(data)

@login_required
@manager_required
@require_POST
def update(request, pk):
    import json
    data=json.loads(request.body or '{}')
    order=SalesOrder.objects.get(pk=pk); d,_=DeliveryRecord.objects.get_or_create(order=order)
    for f in ['delivery_date','address','transport','responsible_person','installation_required','installation_date','status','acknowledgement','completion_notes']:
        if f in data: setattr(d,f,data[f] or None if f.endswith('_date') else data[f])
    d.save()
    if d.status in ['delivered','installed']:
        order.status=SalesOrder.Status.DELIVERED; order.save(update_fields=['status','updated_at'])
    return JsonResponse(_delivery(d))

@login_required
@manager_required
@require_POST
def feedback(request, pk):
    import json
    data=json.loads(request.body or '{}'); order=SalesOrder.objects.get(pk=pk)
    fb,_=CustomerFeedback.objects.get_or_create(order=order)
    fb.rating=data.get('rating') or None; fb.comment=data.get('comment',''); fb.save()
    return JsonResponse({'rating':fb.rating,'comment':fb.comment})
