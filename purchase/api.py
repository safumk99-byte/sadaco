import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserProfile
from products.models import Product
from products.inventory import record_stock_transaction
from .forms import SupplierForm, PurchaseOrderForm, PurchaseItemForm, GoodsReceiptForm
from .models import Supplier, PurchaseOrder, PurchaseItem, GoodsReceipt

MANAGER_ROLES = {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER}

def _manager(user):
    return user.is_superuser or getattr(getattr(user, 'profile', None), 'role', None) in MANAGER_ROLES

def _choices(choices): return [{'value': v, 'label': l} for v, l in choices]
def _supplier(s):
    return {'id': s.id, 'name': s.name, 'contact_person': s.contact_person, 'phone': s.phone, 'email': s.email,
            'address': s.address, 'tax_number': s.tax_number, 'payment_terms': s.payment_terms, 'notes': s.notes,
            'status': s.status, 'status_label': s.get_status_display()}
def _item(i):
    return {'id': i.id, 'product': {'id': i.product_id, 'name': i.product.name, 'sku': i.product.sku} if i.product else None,
            'quantity': str(i.quantity), 'received_quantity': str(i.received_quantity), 'pending_quantity': str(i.pending_quantity),
            'unit_cost': str(i.unit_cost), 'line_total': str(i.line_total), 'notes': i.notes}
def _po(po):
    return {'id': po.id, 'po_no': po.po_no, 'supplier': _supplier(po.supplier), 'order_date': po.order_date.isoformat(),
            'expected_date': po.expected_date.isoformat() if po.expected_date else None, 'status': po.status,
            'status_label': po.get_status_display(), 'notes': po.notes, 'subtotal': str(po.subtotal), 'discount': str(po.discount),
            'tax': str(po.tax), 'total': str(po.total), 'created_by': po.created_by.get_full_name() if po.created_by else None,
            'items': [_item(i) for i in po.items.select_related('product').all()],
            'receipts': [{'id': r.id, 'receipt_no': r.receipt_no, 'received_date': r.received_date.isoformat(),
                          'supplier_reference': r.supplier_reference, 'notes': r.notes} for r in po.receipts.all()]}

def _data(request):
    try: return json.loads(request.body or '{}')
    except (TypeError, ValueError): return {}

def _deny(user):
    if not _manager(user): raise PermissionDenied

@require_GET
@login_required
def summary(request):
    orders = PurchaseOrder.objects.exclude(status=PurchaseOrder.Status.CANCELLED)
    return JsonResponse({'stats': {
        'draft': PurchaseOrder.objects.filter(status=PurchaseOrder.Status.DRAFT).count(),
        'open_orders': PurchaseOrder.objects.filter(status__in=[PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIAL]).count(),
        'received': PurchaseOrder.objects.filter(status=PurchaseOrder.Status.RECEIVED).count(),
        'total_value': str(orders.aggregate(total=Sum('total'))['total'] or 0),
        'suppliers': Supplier.objects.filter(status=Supplier.Status.ACTIVE).count(),
    }})

@require_GET
@login_required
def suppliers(request):
    _deny(request.user)
    q=request.GET.get('q','').strip(); status=request.GET.get('status','')
    qs=Supplier.objects.all()
    if q: qs=qs.filter(Q(name__icontains=q)|Q(phone__icontains=q)|Q(email__icontains=q)|Q(contact_person__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'suppliers': [_supplier(s) for s in qs[:300]], 'can_manage': True,
                         'statuses': _choices(Supplier.Status.choices)})

@require_POST
@login_required
def supplier_create(request):
    _deny(request.user); form=SupplierForm(_data(request))
    if form.is_valid(): return JsonResponse({'supplier': _supplier(form.save())}, status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()}, status=400)

@require_POST
@login_required
def supplier_update(request, pk):
    _deny(request.user); s=get_object_or_404(Supplier, pk=pk); form=SupplierForm(_data(request), instance=s)
    if form.is_valid(): return JsonResponse({'supplier': _supplier(form.save())})
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()}, status=400)

@require_GET
@login_required
def orders(request):
    _deny(request.user); q=request.GET.get('q','').strip(); status=request.GET.get('status','')
    qs=PurchaseOrder.objects.select_related('supplier','created_by').prefetch_related('items__product','receipts')
    if q: qs=qs.filter(Q(po_no__icontains=q)|Q(supplier__name__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'orders': [_po(x) for x in qs[:250]], 'statuses': _choices(PurchaseOrder.Status.choices),
                         'suppliers': [_supplier(s) for s in Supplier.objects.filter(status=Supplier.Status.ACTIVE)],
                         'products': [{'id':p.id,'name':p.name,'sku':p.sku} for p in Product.objects.filter(status=Product.Status.ACTIVE)[:300]]})

@require_GET
@login_required
def detail(request, pk):
    _deny(request.user); return JsonResponse({'order': _po(get_object_or_404(PurchaseOrder.objects.select_related('supplier','created_by').prefetch_related('items__product','receipts'), pk=pk))})

@require_POST
@login_required
@transaction.atomic
def create(request):
    _deny(request.user); data=_data(request)
    po_form=PurchaseOrderForm(data); item_form=PurchaseItemForm(data)
    if po_form.is_valid() and item_form.is_valid():
        po=po_form.save(commit=False); po.created_by=request.user
        po.subtotal=item_form.cleaned_data['quantity'] * item_form.cleaned_data['unit_cost']; po.save()
        item=item_form.save(commit=False); item.purchase_order=po; item.save()
        return JsonResponse({'order':_po(po)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':{**po_form.errors.get_json_data(), **item_form.errors.get_json_data()}},status=400)

@require_POST
@login_required
@transaction.atomic
def receive(request, pk):
    _deny(request.user); po=get_object_or_404(PurchaseOrder.objects.select_for_update().prefetch_related('items__product'), pk=pk)
    form=GoodsReceiptForm(_data(request))
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    receipt=form.save(commit=False); receipt.purchase_order=po; receipt.received_by=request.user; receipt.save()
    for item in po.items.all():
        qty=item.pending_quantity
        if qty <= 0: continue
        record_stock_transaction(product_id=item.product_id, transaction_type='in', quantity=qty, user=request.user,
                                  reference=receipt.receipt_no, remarks=f'Goods received for {po.po_no}.')
        item.received_quantity += qty; item.save(update_fields=['received_quantity'])
    po.status=PurchaseOrder.Status.RECEIVED; po.save(update_fields=['status','updated_at'])
    return JsonResponse({'order':_po(po), 'receipt':{'receipt_no':receipt.receipt_no}})
