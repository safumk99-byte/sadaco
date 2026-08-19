from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Notification, UserProfile
from products.inventory import record_stock_transaction
from products.models import Product
from .forms import SupplierForm, PurchaseOrderForm, PurchaseItemForm, GoodsReceiptForm
from .models import Supplier, PurchaseOrder, PurchaseItem, GoodsReceipt

manager_required = role_required("super_admin","institution_admin","manager")


@login_required
@manager_required
def dashboard(request):
    q=request.GET.get("q","").strip()
    orders=PurchaseOrder.objects.select_related("supplier")
    if q:
        orders=orders.filter(Q(po_no__icontains=q)|Q(supplier__name__icontains=q))
    context={
        "title":"Purchase Management",
        "orders":orders[:50],
        "suppliers":Supplier.objects.filter(status=Supplier.Status.ACTIVE),
        "draft":PurchaseOrder.objects.filter(status=PurchaseOrder.Status.DRAFT).count(),
        "open_orders":PurchaseOrder.objects.filter(status__in=[PurchaseOrder.Status.SENT,PurchaseOrder.Status.PARTIAL]).count(),
        "received":PurchaseOrder.objects.filter(status=PurchaseOrder.Status.RECEIVED).count(),
        "total_value":PurchaseOrder.objects.exclude(status=PurchaseOrder.Status.CANCELLED).aggregate(total=Sum("total"))["total"] or 0,
        "query":q,
    }
    return render(request,"purchase/dashboard.html",context)


@login_required
@manager_required
def supplier_list(request):
    return render(request,"purchase/suppliers.html",{
        "title":"Suppliers",
        "suppliers":Supplier.objects.all(),
    })


@login_required
@manager_required
def supplier_create(request):
    form=SupplierForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        form.save()
        messages.success(request,"Supplier created.")
        return redirect("purchase:suppliers")
    return render(request,"purchase/form.html",{"title":"Add Supplier","form":form,"back":"purchase:dashboard"})


@login_required
@manager_required
@transaction.atomic
def purchase_create(request):
    po_form=PurchaseOrderForm(request.POST or None)
    item_form=PurchaseItemForm(request.POST or None)
    if request.method=="POST" and po_form.is_valid() and item_form.is_valid():
        po=po_form.save(commit=False)
        po.created_by=request.user
        po.subtotal=item_form.cleaned_data["quantity"]*item_form.cleaned_data["unit_cost"]
        po.save()
        item= item_form.save(commit=False)
        item.purchase_order=po
        item.save()
        messages.success(request,f"{po.po_no} created.")
        return redirect("purchase:purchase_detail",pk=po.pk)
    return render(request,"purchase/purchase_form.html",{"title":"Create Purchase Order","po_form":po_form,"item_form":item_form})


@login_required
@manager_required
def purchase_detail(request,pk):
    po=get_object_or_404(PurchaseOrder.objects.select_related("supplier").prefetch_related("items__product","receipts"),pk=pk)
    return render(request,"purchase/detail.html",{"title":po.po_no,"po":po})


@login_required
@manager_required
@transaction.atomic
def receive_purchase(request,pk):
    po=get_object_or_404(PurchaseOrder.objects.select_for_update().prefetch_related("items__product"),pk=pk)
    form=GoodsReceiptForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        receipt=form.save(commit=False)
        receipt.purchase_order=po
        receipt.received_by=request.user
        receipt.save()

        for item in po.items.all():
            if item.pending_quantity <= 0:
                continue
            qty=item.pending_quantity
            record_stock_transaction(
                product_id=item.product_id,
                transaction_type="in",
                quantity=qty,
                user=request.user,
                reference=receipt.receipt_no,
                remarks=f"Goods received for {po.po_no}.",
            )
            item.received_quantity += qty
            item.save(update_fields=["received_quantity"])

        po.status=PurchaseOrder.Status.RECEIVED
        po.save(update_fields=["status","updated_at"])

        for profile in UserProfile.objects.filter(
            role__in=[UserProfile.Role.SUPER_ADMIN,UserProfile.Role.INSTITUTION_ADMIN,UserProfile.Role.MANAGER],
            is_active=True,
        ):
            Notification.objects.create(
                user=profile.user,
                notification_type=Notification.Type.STOCK,
                priority=Notification.Priority.NORMAL,
                title="Goods received",
                message=f"{po.po_no} received and stock updated.",
                url=f"/purchase/orders/{po.pk}/",
            )
        messages.success(request,f"{receipt.receipt_no} recorded and stock updated.")
        return redirect("purchase:purchase_detail",pk=po.pk)
    return render(request,"purchase/receive.html",{"title":f"Receive {po.po_no}","po":po,"form":form})
