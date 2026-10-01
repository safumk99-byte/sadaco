from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.views.decorators.http import require_http_methods

from accounts.models import UserProfile
from staff.models import StaffProfile
from .forms import CustomerForm, EnquiryForm, QuotationForm, SalesOrderForm
from .models import Customer, Enquiry, Quotation, SalesOrder, OrderRequest

MANAGER_ROLES = {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER}

def _manager(user):
    return user.is_superuser or (getattr(getattr(user, 'profile', None), 'is_active', False) and getattr(user.profile, 'role', None) in MANAGER_ROLES)

def _guard(user, manager=False):
    if not user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)
    if manager and not _manager(user):
        raise PermissionDenied
    return None

def _choice(value, label): return {'value': value, 'label': label}

def _customer(c): return {'id': c.id, 'name': c.name, 'phone': c.phone, 'email': c.email, 'status': c.status, 'status_label': c.get_status_display()}
def _enquiry(e): return {'id': e.id, 'enquiry_no': e.enquiry_no, 'customer': _customer(e.customer), 'channel': e.channel, 'channel_label': e.get_channel_display(), 'product_type': e.product_type, 'quantity': str(e.quantity), 'status': e.status, 'status_label': e.get_status_display(), 'deadline': e.deadline.isoformat() if e.deadline else None, 'expected_delivery_date': e.expected_delivery_date.isoformat() if e.expected_delivery_date else None, 'assigned_to': e.assigned_to.get_full_name() or e.assigned_to.username if e.assigned_to else None}
def _quotation(q): return {'id': q.id, 'quotation_no': q.quotation_no, 'customer': _customer(q.customer), 'item_description': q.item_description, 'quantity': str(q.quantity), 'cost_total': str(q.cost_total), 'quoted_price': str(q.quoted_price), 'advance_required': str(q.advance_required), 'valid_until': q.valid_until.isoformat() if q.valid_until else None, 'status': q.status, 'status_label': q.get_status_display()}
def _order(o): return {'id': o.id, 'order_no': o.order_no, 'customer': _customer(o.customer), 'item_description': o.item_description, 'quantity': str(o.quantity), 'confirmed_price': str(o.confirmed_price), 'delivery_date': o.delivery_date.isoformat() if o.delivery_date else None, 'deadline': o.deadline.isoformat() if o.deadline else None, 'status': o.status, 'status_label': o.get_status_display(), 'responsible_staff': (o.responsible_staff.user.get_full_name() or o.responsible_staff.user.username) if o.responsible_staff else None}

@login_required
def summary(request):
    return JsonResponse({'stats': {
        'customers': Customer.objects.filter(status=Customer.Status.ACTIVE).count(),
        'new_enquiries': Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
        'quotations': Quotation.objects.exclude(status=Quotation.Status.CONVERTED).count(),
        'open_orders': SalesOrder.objects.exclude(status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]).count(),
        'pending_requests': OrderRequest.objects.filter(status__in=[OrderRequest.Status.NEW, OrderRequest.Status.REVIEWING, OrderRequest.Status.CONTACTED]).count(),
    }, 'recent_enquiries': [_enquiry(x) for x in Enquiry.objects.select_related('customer','assigned_to')[:6]], 'recent_orders': [_order(x) for x in SalesOrder.objects.select_related('customer','responsible_staff__user')[:6]]})

@login_required
def customers(request):
    q = request.GET.get('q','').strip(); qs = Customer.objects.all()
    if q: qs = qs.filter(Q(name__icontains=q)|Q(phone__icontains=q)|Q(email__icontains=q))
    return JsonResponse({'customers': [_customer(x) for x in qs[:250]], 'can_manage': _manager(request.user)})

@require_http_methods(['POST'])
@login_required
def customer_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; form = CustomerForm(json.loads(request.body or '{}'))
    if form.is_valid():
        c=form.save(); return JsonResponse({'customer': _customer(c)}, status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def customer_update(request, pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; c=Customer.objects.get(pk=pk); form=CustomerForm(json.loads(request.body or '{}'),instance=c)
    if form.is_valid(): return JsonResponse({'customer':_customer(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@login_required
def enquiries(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=Enquiry.objects.select_related('customer','assigned_to')
    if q: qs=qs.filter(Q(enquiry_no__icontains=q)|Q(customer__name__icontains=q)|Q(product_type__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'enquiries':[_enquiry(x) for x in qs[:250]],'can_manage':_manager(request.user),'statuses':[_choice(v,l) for v,l in Enquiry.Status.choices]})

@require_http_methods(['POST'])
@login_required
def enquiry_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; data=json.loads(request.body or '{}'); form=EnquiryForm(data)
    if form.is_valid():
        e=form.save(commit=False); e.created_by=request.user; e.save(); return JsonResponse({'enquiry':_enquiry(e)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def enquiry_update(request,pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; e=Enquiry.objects.get(pk=pk); form=EnquiryForm(json.loads(request.body or '{}'),instance=e)
    if form.is_valid(): return JsonResponse({'enquiry':_enquiry(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@login_required
def quotations(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=Quotation.objects.select_related('customer')
    if q: qs=qs.filter(Q(quotation_no__icontains=q)|Q(customer__name__icontains=q)|Q(item_description__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'quotations':[_quotation(x) for x in qs[:250]],'can_manage':_manager(request.user),'statuses':[_choice(v,l) for v,l in Quotation.Status.choices]})

@require_http_methods(['POST'])
@login_required
def quotation_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; form=QuotationForm(json.loads(request.body or '{}'))
    if form.is_valid():
        q=form.save(commit=False); q.created_by=request.user; q.save(); return JsonResponse({'quotation':_quotation(q)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def quotation_update(request,pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; q=Quotation.objects.get(pk=pk); form=QuotationForm(json.loads(request.body or '{}'),instance=q)
    if form.is_valid(): return JsonResponse({'quotation':_quotation(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@login_required
def orders(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=SalesOrder.objects.select_related('customer','responsible_staff__user')
    if q: qs=qs.filter(Q(order_no__icontains=q)|Q(customer__name__icontains=q)|Q(item_description__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'orders':[_order(x) for x in qs[:250]],'can_manage':_manager(request.user),'statuses':[_choice(v,l) for v,l in SalesOrder.Status.choices]})

@require_http_methods(['POST'])
@login_required
def order_create(request):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; form=SalesOrderForm(json.loads(request.body or '{}'))
    if form.is_valid():
        o=form.save(commit=False); o.created_by=request.user; o.save(); return JsonResponse({'order':_order(o)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)

@require_http_methods(['POST'])
@login_required
def order_update(request,pk):
    if _guard(request.user, True): return _guard(request.user, True)
    import json; o=SalesOrder.objects.get(pk=pk); form=SalesOrderForm(json.loads(request.body or '{}'),instance=o)
    if form.is_valid(): return JsonResponse({'order':_order(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
