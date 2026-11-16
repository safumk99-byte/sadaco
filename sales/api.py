from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import UserProfile
from core.models import Department
from staff.models import StaffProfile
from .forms import CustomerForm, CustomerInteractionForm, EnquiryForm, QuotationForm, SalesOrderForm
from .models import Customer, CustomerInteraction, Enquiry, Quotation, SalesOrder, OrderRequest

MANAGER_ROLES = {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER}

def _manager(user):
    return user.is_superuser or (getattr(getattr(user, 'profile', None), 'is_active', False) and getattr(user.profile, 'role', None) in MANAGER_ROLES)

def _guard(user, manager=False):
    if not user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)
    if manager and not _manager(user):
        raise PermissionDenied
    return None

def _global_admin(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(
        profile and profile.is_active and profile.role in (
            UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN
        )
    )


def _department_id(user):
    profile = getattr(user, "profile", None)
    return profile.department_id if profile and profile.role == UserProfile.Role.MANAGER else None


def _customer_qs(user):
    qs = Customer.objects.all()
    if _global_admin(user):
        return qs
    if getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.MANAGER:
        department_id = _department_id(user)
        return qs.filter(department_id=department_id) if department_id else qs.none()
    return qs.filter(
        Q(enquiries__assigned_to=user) | Q(enquiries__created_by=user)
        | Q(quotations__created_by=user) | Q(orders__created_by=user)
        | Q(orders__responsible_staff__user=user)
    ).distinct()


def _enquiry_qs(user):
    qs = Enquiry.objects.all()
    if _global_admin(user):
        return qs
    if getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.MANAGER:
        department_id = _department_id(user)
        return qs.filter(customer__department_id=department_id) if department_id else qs.none()
    return qs.filter(Q(assigned_to=user) | Q(created_by=user))


def _quotation_qs(user):
    qs = Quotation.objects.all()
    if _global_admin(user):
        return qs
    if getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.MANAGER:
        department_id = _department_id(user)
        return qs.filter(customer__department_id=department_id) if department_id else qs.none()
    return qs.filter(created_by=user)


def _order_qs(user):
    qs = SalesOrder.objects.all()
    if _global_admin(user):
        return qs
    if getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.MANAGER:
        department_id = _department_id(user)
        return qs.filter(customer__department_id=department_id) if department_id else qs.none()
    return qs.filter(Q(created_by=user) | Q(responsible_staff__user=user))


def _order_status_error(current_status, new_status):
    if current_status == new_status:
        return None
    sales_managed = {SalesOrder.Status.CONFIRMED, SalesOrder.Status.DESIGN_PENDING}
    if current_status in sales_managed and new_status in sales_managed | {SalesOrder.Status.CANCELLED}:
        return None
    return "Production, quality and delivery statuses can only be changed by their respective modules."


def _restrict_form(form, user, model):
    if model == "enquiry":
        form.fields["customer"].queryset = _customer_qs(user).filter(status=Customer.Status.ACTIVE)
        form.fields["assigned_to"].queryset = form.fields["assigned_to"].queryset.filter(
            profile__department_id=_department_id(user)
        ) if not _global_admin(user) and _department_id(user) else (
            form.fields["assigned_to"].queryset if _global_admin(user) else form.fields["assigned_to"].queryset.none()
        )
    elif model == "quotation":
        form.fields["customer"].queryset = _customer_qs(user).filter(status=Customer.Status.ACTIVE)
        form.fields["enquiry"].queryset = _enquiry_qs(user)
        form.fields["order_request"].queryset = OrderRequest.objects.filter(customer__in=_customer_qs(user))
    elif model == "order":
        form.fields["customer"].queryset = _customer_qs(user).filter(status=Customer.Status.ACTIVE)
        form.fields["quotation"].queryset = _quotation_qs(user)
        staff_qs = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).select_related("user")
        if not _global_admin(user):
            department_id = _department_id(user)
            staff_qs = staff_qs.filter(department_id=department_id) if department_id else staff_qs.none()
        form.fields["responsible_staff"].queryset = staff_qs
    return form

def _choice(value, label): return {'value': value, 'label': label}

def _customer(c): return {'id': c.id, 'customer_no': c.customer_no, 'name': c.name, 'customer_type': c.customer_type, 'phone': c.phone, 'email': c.email, 'status': c.status, 'status_label': c.get_status_display(), 'department': {'id': c.department_id, 'name': c.department.name} if c.department_id else None}
def _enquiry(e): return {'id': e.id, 'enquiry_no': e.enquiry_no, 'customer': _customer(e.customer), 'channel': e.channel, 'channel_label': e.get_channel_display(), 'product_type': e.product_type, 'quantity': str(e.quantity), 'status': e.status, 'status_label': e.get_status_display(), 'deadline': e.deadline.isoformat() if e.deadline else None, 'expected_delivery_date': e.expected_delivery_date.isoformat() if e.expected_delivery_date else None, 'assigned_to': e.assigned_to.get_full_name() or e.assigned_to.username if e.assigned_to else None}
def _quotation(q): return {'id': q.id, 'quotation_no': q.quotation_no, 'customer': _customer(q.customer), 'item_description': q.item_description, 'dimensions': q.dimensions, 'quantity': str(q.quantity), 'cost_total': str(q.cost_total), 'subtotal': str(q.subtotal), 'discount_percent': str(q.discount_percent), 'discount_amount': str(q.discount_amount), 'tax_rate': str(q.tax_rate) if q.tax_rate is not None else None, 'tax_amount': str(q.tax_amount), 'quoted_price': str(q.quoted_price), 'advance_required': str(q.advance_required), 'valid_until': q.valid_until.isoformat() if q.valid_until else None, 'status': q.status, 'status_label': q.get_status_display()}
def _order(o): return {'id': o.id, 'order_no': o.order_no, 'customer': _customer(o.customer), 'item_description': o.item_description, 'quantity': str(o.quantity), 'confirmed_price': str(o.confirmed_price), 'delivery_date': o.delivery_date.isoformat() if o.delivery_date else None, 'deadline': o.deadline.isoformat() if o.deadline else None, 'status': o.status, 'status_label': o.get_status_display(), 'responsible_staff': (o.responsible_staff.user.get_full_name() or o.responsible_staff.user.username) if o.responsible_staff else None}

@login_required
def summary(request):
    customers = _customer_qs(request.user)
    enquiries = _enquiry_qs(request.user)
    quotations = _quotation_qs(request.user)
    orders = _order_qs(request.user)
    requests = OrderRequest.objects.filter(customer__in=customers)
    return JsonResponse({'stats': {
        'customers': customers.filter(status=Customer.Status.ACTIVE).count(),
        'new_enquiries': enquiries.filter(status=Enquiry.Status.NEW).count(),
        'quotations': quotations.exclude(status=Quotation.Status.CONVERTED).count(),
        'open_orders': orders.exclude(status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]).count(),
        'pending_requests': requests.filter(status__in=[OrderRequest.Status.NEW, OrderRequest.Status.REVIEWING, OrderRequest.Status.CONTACTED]).count(),
    }, 'recent_enquiries': [_enquiry(x) for x in enquiries.select_related('customer','assigned_to')[:6]], 'recent_orders': [_order(x) for x in orders.select_related('customer','responsible_staff__user')[:6]]})

@login_required
def customers(request):
    q = request.GET.get('q','').strip(); qs = _customer_qs(request.user)
    if q: qs = qs.filter(Q(name__icontains=q)|Q(phone__icontains=q)|Q(email__icontains=q))
    departments = Department.objects.filter(is_active=True)
    if not _global_admin(request.user):
        department_id = _department_id(request.user)
        departments = departments.filter(pk=department_id) if department_id else departments.none()
    return JsonResponse({
        'customers': [_customer(x) for x in qs.select_related("department")[:250]],
        'can_manage': _manager(request.user),
        'departments': [{'id': d.id, 'name': d.name, 'code': d.code} for d in departments],
    })

@require_http_methods(['POST'])
@login_required
def customer_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; data=json.loads(request.body or '{}'); form = CustomerForm(data)
    if form.is_valid():
        c=form.save(commit=False)
        if not _global_admin(request.user):
            c.department_id = _department_id(request.user)
            if not c.department_id:
                return JsonResponse({'detail': 'Assign your manager account to a department first.'}, status=400)
        elif data.get("department"):
            c.department = get_object_or_404(Department, pk=data.get("department"), is_active=True)
        else:
            return JsonResponse({'detail': 'Select a business division for this customer.'}, status=400)
        c.save(); return JsonResponse({'customer': _customer(c)}, status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def customer_update(request, pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; data=json.loads(request.body or '{}'); c=get_object_or_404(_customer_qs(request.user),pk=pk); form=CustomerForm(data,instance=c)
    if form.is_valid():
        customer=form.save(commit=False)
        if _global_admin(request.user) and data.get("department"):
            customer.department=get_object_or_404(Department,pk=data.get("department"),is_active=True)
        customer.save()
        return JsonResponse({'customer':_customer(customer)})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@login_required
def enquiries(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=_enquiry_qs(request.user).select_related('customer','assigned_to')
    if q: qs=qs.filter(Q(enquiry_no__icontains=q)|Q(customer__name__icontains=q)|Q(product_type__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'enquiries':[_enquiry(x) for x in qs[:250]],'can_manage':_manager(request.user),'statuses':[_choice(v,l) for v,l in Enquiry.Status.choices]})

@require_http_methods(['POST'])
@login_required
def enquiry_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; data=json.loads(request.body or '{}'); form=_restrict_form(EnquiryForm(data), request.user, "enquiry")
    if form.is_valid():
        e=form.save(commit=False); e.created_by=request.user; e.save(); return JsonResponse({'enquiry':_enquiry(e)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def enquiry_update(request,pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; e=get_object_or_404(_enquiry_qs(request.user),pk=pk); form=_restrict_form(EnquiryForm(json.loads(request.body or '{}'),instance=e), request.user, "enquiry")
    if form.is_valid(): return JsonResponse({'enquiry':_enquiry(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@login_required
def quotations(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=_quotation_qs(request.user).select_related('customer')
    if q: qs=qs.filter(Q(quotation_no__icontains=q)|Q(customer__name__icontains=q)|Q(item_description__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'quotations':[_quotation(x) for x in qs[:250]],'can_manage':_manager(request.user),'statuses':[_choice(v,l) for v,l in Quotation.Status.choices]})

@require_http_methods(['POST'])
@login_required
def quotation_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; data=json.loads(request.body or '{}'); data["status"] = Quotation.Status.DRAFT
    form=_restrict_form(QuotationForm(data), request.user, "quotation")
    if form.is_valid():
        q=form.save(commit=False); q.created_by=request.user; q.status=Quotation.Status.DRAFT; q.save(); return JsonResponse({'quotation':_quotation(q)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def quotation_update(request,pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; q=get_object_or_404(_quotation_qs(request.user),pk=pk)
    if q.status != Quotation.Status.DRAFT:
        return JsonResponse({"detail": "Only Draft quotations can be edited. Use the approval workflow for submitted quotations."}, status=409)
    data=json.loads(request.body or '{}'); data["status"] = Quotation.Status.DRAFT
    form=_restrict_form(QuotationForm(data,instance=q), request.user, "quotation")
    if form.is_valid():
        saved=form.save(commit=False); saved.status=Quotation.Status.DRAFT; saved.save()
        return JsonResponse({'quotation':_quotation(saved)})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@login_required
def orders(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=_order_qs(request.user).select_related('customer','responsible_staff__user')
    if q: qs=qs.filter(Q(order_no__icontains=q)|Q(customer__name__icontains=q)|Q(item_description__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'orders':[_order(x) for x in qs[:250]],'can_manage':_manager(request.user),'statuses':[_choice(v,l) for v,l in SalesOrder.Status.choices]})

@require_http_methods(['POST'])
@login_required
def order_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; form=_restrict_form(SalesOrderForm(json.loads(request.body or '{}')), request.user, "order")
    if form.is_valid():
        if form.cleaned_data["status"] not in (SalesOrder.Status.CONFIRMED, SalesOrder.Status.DESIGN_PENDING):
            return JsonResponse({"detail": "A new sales order must start as Confirmed or Design Pending. Production and delivery statuses are managed by their respective modules."}, status=400)
        o=form.save(commit=False); o.created_by=request.user; o.save(); return JsonResponse({'order':_order(o)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def order_update(request,pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; o=get_object_or_404(_order_qs(request.user),pk=pk); data=json.loads(request.body or '{}')
    requested_status = data.get("status")
    if requested_status is not None:
        status_error = _order_status_error(o.status, requested_status)
        if status_error:
            return JsonResponse({"detail": status_error}, status=400)
    form=_restrict_form(SalesOrderForm(data,instance=o), request.user, "order")
    if form.is_valid():
        status_error = _order_status_error(o.status, form.cleaned_data["status"])
        if status_error:
            return JsonResponse({"detail": status_error}, status=400)
        return JsonResponse({'order':_order(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)


@login_required
def customer_interactions(request, pk):
    customer = get_object_or_404(_customer_qs(request.user), pk=pk)
    if request.method == "GET":
        today = timezone.localdate()
        records = customer.interactions.select_related("created_by").all()[:200]
        return JsonResponse({"interactions": [{
            "id": item.pk,
            "interaction_type": item.interaction_type,
            "interaction_type_label": item.get_interaction_type_display(),
            "subject": item.subject,
            "notes": item.notes,
            "next_follow_up": item.next_follow_up.isoformat() if item.next_follow_up else None,
            "completed": item.completed,
            "overdue": bool(item.next_follow_up and not item.completed and item.next_follow_up < today),
            "created_by": (item.created_by.get_full_name() or item.created_by.username) if item.created_by else "System",
            "created_at": item.created_at.isoformat(),
        } for item in records]})
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    if not _manager(request.user):
        raise PermissionDenied
    import json
    try:
        data = json.loads(request.body or "{}")
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    form = CustomerInteractionForm(data)
    if form.is_valid():
        interaction = form.save(commit=False)
        interaction.customer = customer
        interaction.created_by = request.user
        interaction.save()
        return JsonResponse({"id": interaction.pk}, status=201)
    return JsonResponse({"detail": "Validation failed.", "errors": form.errors.get_json_data()}, status=400)


@login_required
@require_http_methods(["POST"])
def customer_interaction_complete(request, pk, interaction_id):
    if not _manager(request.user):
        raise PermissionDenied
    customer = get_object_or_404(_customer_qs(request.user), pk=pk)
    interaction = get_object_or_404(CustomerInteraction, pk=interaction_id, customer=customer)
    if not interaction.completed:
        interaction.completed = True
        interaction.save(update_fields=["completed"])
    return JsonResponse({"id": interaction.pk, "completed": interaction.completed})
