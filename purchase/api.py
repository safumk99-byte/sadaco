import json
from decimal import Decimal, InvalidOperation
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
from .models import Supplier, PurchaseOrder, PurchaseItem, GoodsReceipt, GoodsReceiptLine, MaterialStockLot

MANAGER_ROLES = {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER}

def _manager(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(profile and profile.is_active and profile.role in MANAGER_ROLES)

def _choices(choices): return [{'value': v, 'label': l} for v, l in choices]
def _supplier(s):
    return {'id': s.id, 'name': s.name, 'contact_person': s.contact_person, 'phone': s.phone, 'email': s.email,
            'address': s.address, 'tax_number': s.tax_number, 'payment_terms': s.payment_terms, 'notes': s.notes,
            'status': s.status, 'status_label': s.get_status_display()}
def _item(i):
    return {'id': i.id, 'product': {'id': i.product_id, 'name': i.product.name, 'sku': i.product.sku} if i.product else None,
            'material_variant': {'id': i.material_variant_id, 'name': i.material_variant.material_name, 'brand': i.material_variant.brand} if i.material_variant else None,
            'quantity': str(i.quantity), 'received_quantity': str(i.received_quantity), 'pending_quantity': str(i.pending_quantity),
            'unit_cost': str(i.unit_cost), 'line_total': str(i.line_total), 'notes': i.notes}
def _po(po):
    return {'id': po.id, 'po_no': po.po_no, 'department_id': po.department_id, 'department': po.department.name if po.department_id else None, 'supplier': _supplier(po.supplier), 'order_date': po.order_date.isoformat(),
            'expected_date': po.expected_date.isoformat() if po.expected_date else None, 'status': po.status,
            'status_label': po.get_status_display(), 'notes': po.notes, 'subtotal': str(po.subtotal), 'discount': str(po.discount),
            'tax': str(po.tax), 'total': str(po.total), 'created_by': po.created_by.get_full_name() if po.created_by else None,
            'items': [_item(i) for i in po.items.select_related('product').all()],
            'receipts': [{'id': r.id, 'receipt_no': r.receipt_no, 'received_date': r.received_date.isoformat(),
                          'supplier_reference': r.supplier_reference, 'notes': r.notes, 'lines': [{'id': line.id, 'purchase_item_id': line.purchase_item_id, 'received_quantity': str(line.received_quantity), 'unit_cost': str(line.unit_cost), 'line_total': str(line.line_total), 'stock_movement_id': line.material_stock_movement_id} for line in r.lines.all()]} for r in po.receipts.prefetch_related('lines').all()]}

def _data(request):
    try: return json.loads(request.body or '{}')
    except (TypeError, ValueError): return {}

def _deny(user):
    if not _manager(user): raise PermissionDenied

def _global_admin(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(
        profile and profile.is_active and profile.role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)
    )


def _department_id(user):
    profile = getattr(user, "profile", None)
    return profile.department_id if profile and profile.role == UserProfile.Role.MANAGER else None


def _require_department(user):
    if not _global_admin(user) and not _department_id(user):
        raise PermissionDenied("Assign your manager account to a department first.")


def _purchase_orders(user):
    qs = PurchaseOrder.objects.all()
    if _global_admin(user):
        return qs
    department_id = _department_id(user)
    if not department_id:
        return qs.none()
    return qs.filter(
        Q(department_id=department_id) |
        Q(department__isnull=True, created_by__profile__department_id=department_id)
    )

@require_GET
@login_required
def summary(request):
    _deny(request.user)
    visible = _purchase_orders(request.user)
    orders = visible.exclude(status=PurchaseOrder.Status.CANCELLED)
    return JsonResponse({'stats': {
        'draft': visible.filter(status=PurchaseOrder.Status.DRAFT).count(),
        'open_orders': visible.filter(status__in=[PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIAL]).count(),
        'received': visible.filter(status=PurchaseOrder.Status.RECEIVED).count(),
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
    qs=_purchase_orders(request.user).select_related('supplier','created_by').prefetch_related('items__product','receipts')
    if q: qs=qs.filter(Q(po_no__icontains=q)|Q(supplier__name__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'orders': [_po(x) for x in qs[:250]], 'statuses': _choices(PurchaseOrder.Status.choices),
                         'suppliers': [_supplier(s) for s in Supplier.objects.filter(status=Supplier.Status.ACTIVE)],
                         'products': [{'id':p.id,'name':p.name,'sku':p.sku} for p in Product.objects.filter(status=Product.Status.ACTIVE)[:300]],
                         'materials': [{'id':m.id,'name':m.material_name,'brand':m.brand,'unit':m.unit} for m in __import__('products.models', fromlist=['MaterialVariant']).MaterialVariant.objects.filter(is_active=True)[:500]]})

@require_GET
@login_required
def detail(request, pk):
    _deny(request.user); return JsonResponse({'order': _po(get_object_or_404(_purchase_orders(request.user).select_related('supplier','created_by').prefetch_related('items__product','receipts'), pk=pk))})

@require_POST
@login_required
@transaction.atomic
def create(request):
    _deny(request.user); _require_department(request.user); data=_data(request)
    po_form=PurchaseOrderForm(data); item_form=PurchaseItemForm(data)
    if po_form.is_valid() and item_form.is_valid():
        if po_form.cleaned_data["status"] not in (PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.SENT):
            return JsonResponse({"detail": "A new purchase order must be Draft or Sent. Use Goods Receipt to record received stock."}, status=400)
        po=po_form.save(commit=False); po.created_by=request.user
        department_id = _department_id(request.user)
        if _global_admin(request.user):
            department_id = data.get("department")
        if not department_id:
            return JsonResponse({"detail": "Select a department for this purchase order."}, status=400)
        from core.models import Department
        po.department = get_object_or_404(Department, pk=department_id, is_active=True)
        po.subtotal=item_form.cleaned_data['quantity'] * item_form.cleaned_data['unit_cost']; po.save()
        item=item_form.save(commit=False); item.purchase_order=po; item.save()
        return JsonResponse({'order':_po(po)},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':{**po_form.errors.get_json_data(), **item_form.errors.get_json_data()}},status=400)

@require_POST
@login_required
@transaction.atomic
def receive(request, pk):
    _deny(request.user); po=get_object_or_404(_purchase_orders(request.user).select_for_update(of=("self",)).prefetch_related('items__product'), pk=pk)
    if po.status in (PurchaseOrder.Status.CANCELLED, PurchaseOrder.Status.RECEIVED):
        return JsonResponse({"detail": "Cancelled or already received purchase orders cannot receive goods again."}, status=400)
    if po.status not in (PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIAL):
        return JsonResponse({"detail": "Only Sent or Partially Received purchase orders can receive goods."}, status=400)
    form=GoodsReceiptForm(_data(request))
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    data = _data(request)
    location = str(data.get("location", "")).strip()
    pending_items = list(po.items.select_related("material_variant", "product").all())
    items_by_id = {item.pk: item for item in pending_items}

    # Backward compatibility: old clients that do not send per-line quantities
    # continue to receive every pending item. New clients send an explicit list.
    raw_lines = data.get("items")
    receive_quantities = {}
    if raw_lines is None:
        receive_quantities = {
            item.pk: item.pending_quantity for item in pending_items if item.pending_quantity > 0
        }
    else:
        if not isinstance(raw_lines, list) or not raw_lines:
            return JsonResponse({"detail": "Provide at least one purchase item quantity to receive."}, status=400)
        for line in raw_lines:
            if not isinstance(line, dict):
                return JsonResponse({"detail": "Each receipt item must be an object."}, status=400)
            try:
                item_id = int(line.get("purchase_item_id"))
                qty = Decimal(str(line.get("received_quantity")))
            except (TypeError, ValueError, InvalidOperation):
                return JsonResponse({"detail": "Each receipt item needs a valid purchase item ID and quantity."}, status=400)
            if item_id in receive_quantities:
                return JsonResponse({"detail": "A purchase item can appear only once in a receipt."}, status=400)
            item = items_by_id.get(item_id)
            if item is None:
                return JsonResponse({"detail": "A receipt item does not belong to this purchase order."}, status=400)
            if not qty.is_finite() or qty < 0:
                return JsonResponse({"detail": "Received quantities must be zero or greater."}, status=400)
            if max(-qty.as_tuple().exponent, 0) > 2:
                return JsonResponse({"detail": "Received quantities support up to 2 decimal places."}, status=400)
            if qty > item.pending_quantity:
                return JsonResponse({
                    "detail": f"Received quantity for item {item.pk} exceeds its pending quantity ({item.pending_quantity})."
                }, status=400)
            receive_quantities[item_id] = qty

    selected_items = [
        item for item in pending_items if receive_quantities.get(item.pk, Decimal("0")) > 0
    ]
    if not selected_items:
        return JsonResponse({"detail": "Enter a quantity greater than zero for at least one item."}, status=400)
    if any(not (item.material_variant_id or item.product_id) for item in selected_items):
        return JsonResponse({"detail": "Every received purchase item must be linked to a stock item."}, status=400)
    if any(item.material_variant_id for item in selected_items) and not location:
        return JsonResponse({"detail": "A stock location is required to receive material master items."}, status=400)

    receipt=form.save(commit=False); receipt.purchase_order=po; receipt.received_by=request.user; receipt.save()
    from inventory.models import MaterialStockBalance, MaterialStockMovement
    from inventory.services import record_material_movement
    from products.models import MaterialVariant
    for item in selected_items:
        qty = receive_quantities[item.pk]
        if item.material_variant_id:
            balance, _ = MaterialStockBalance.objects.get_or_create(
                material_id=item.material_variant_id, department_id=po.department_id, location=location,
            )
            movement = record_material_movement(
                balance_id=balance.pk, movement_type=MaterialStockMovement.Type.PURCHASE_RECEIPT,
                quantity=qty, user=request.user, reference=receipt.receipt_no,
                remarks=f"Goods received for {po.po_no}.",
            )
            material_master = MaterialVariant.objects.get(pk=item.material_variant_id)
            material_master._rate_changed_by = request.user
            material_master.purchase_rate = item.unit_cost
            material_master.save(update_fields=["purchase_rate", "updated_at"])
        elif item.product_id:
            movement = None
            record_stock_transaction(product_id=item.product_id, transaction_type='in', quantity=qty, user=request.user,
                                      reference=receipt.receipt_no, remarks=f'Goods received for {po.po_no}.')
        else:
            return JsonResponse({"detail": f"Purchase item {item.pk} has no stock item linked."}, status=400)
        receipt_line = GoodsReceiptLine.objects.create(
            receipt=receipt, purchase_item=item, received_quantity=qty,
            unit_cost=item.unit_cost, line_total=qty * item.unit_cost,
            material_stock_movement=movement if item.material_variant_id else None,
        )
        if item.material_variant_id:
            MaterialStockLot.objects.create(
                receipt_line=receipt_line, balance=balance,
                original_quantity=qty, remaining_quantity=qty, unit_cost=item.unit_cost,
            )
        item.received_quantity += qty; item.save(update_fields=['received_quantity'])
    from django.db.models import F
    remaining = po.items.filter(received_quantity__lt=F('quantity')).exists()
    po.status = PurchaseOrder.Status.PARTIAL if remaining else PurchaseOrder.Status.RECEIVED
    po.save(update_fields=['status','updated_at'])
    return JsonResponse({'order':_po(po), 'receipt':{'receipt_no':receipt.receipt_no}})
