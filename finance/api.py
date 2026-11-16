import json
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from accounts.models import UserProfile
from sales.models import PaymentRecord, SalesOrder
from purchase.models import PurchaseOrder
from .forms import ExpenseForm, ExpenseCategoryForm, CustomerPaymentForm, SupplierPaymentForm
from .models import Expense, ExpenseCategory, FinanceTransaction, SupplierPayment, ApprovalThreshold
MANAGER_ROLES={UserProfile.Role.SUPER_ADMIN,UserProfile.Role.INSTITUTION_ADMIN,UserProfile.Role.MANAGER}
def _manager(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(profile and profile.is_active and profile.role in MANAGER_ROLES)
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


def _department_expenses(user):
    qs = Expense.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return qs.filter(created_by__profile__department_id=department_id) if department_id else qs.none()


def _department_orders(user):
    qs = SalesOrder.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return qs.filter(customer__department_id=department_id) if department_id else qs.none()


def _department_purchase_orders(user):
    qs = PurchaseOrder.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    return qs.filter(created_by__profile__department_id=department_id) if department_id else qs.none()


def _department_transactions(user):
    qs = FinanceTransaction.objects.all()
    if _global_admin(user): return qs
    department_id = _department_id(user)
    if not department_id:
        return qs.none()
    # Use the linked business record as the source of truth whenever one exists.
    # Only standalone transactions (e.g. supplier payments) are scoped by creator.
    return qs.filter(
        Q(sales_payment__order__customer__department_id=department_id)
        | Q(expense__created_by__profile__department_id=department_id)
        | Q(supplier_payment__purchase_order__created_by__profile__department_id=department_id)
        | Q(sales_payment__isnull=True, expense__isnull=True, supplier_payment__isnull=True,
            created_by__profile__department_id=department_id)
    ).distinct()
def _choices(c): return [{'value':v,'label':l} for v,l in c]
def _data(r):
    try:return json.loads(r.body or '{}')
    except:return {}
def _expense(x): return {'id':x.id,'expense_no':x.expense_no,'category':{'id':x.category_id,'name':x.category.name},'amount':str(x.amount),'expense_date':x.expense_date.isoformat(),'payment_method':x.payment_method,'reference':x.reference,'description':x.description,'status':x.status,'status_label':x.get_status_display()}
def _tx(x): return {'id':x.id,'transaction_no':x.transaction_no,'type':x.transaction_type,'type_label':x.get_transaction_type_display(),'amount':str(x.amount),'date':x.transaction_date.isoformat(),'payment_method':x.payment_method,'reference':x.reference,'description':x.description,'status':x.status,'status_label':x.get_status_display()}
def _sp(x): return {'id':x.id,'payment_no':x.payment_no,'purchase_order':{'id':x.purchase_order_id,'po_no':x.purchase_order.po_no,'supplier':x.purchase_order.supplier.name},'amount':str(x.amount),'payment_date':x.payment_date.isoformat(),'payment_method':x.payment_method,'reference':x.reference,'status':x.status,'status_label':x.get_status_display(),'notes':x.notes}
def _received(order): return order.payments.filter(status__in=[PaymentRecord.Status.RECEIVED,PaymentRecord.Status.VERIFIED]).aggregate(total=Sum('amount'))['total'] or 0
@require_GET
@login_required
def dashboard(request):
    _deny(request.user)
    orders = _department_orders(request.user).exclude(status=SalesOrder.Status.CANCELLED)
    purchase_orders = _department_purchase_orders(request.user).exclude(status=PurchaseOrder.Status.CANCELLED)
    expenses_qs = _department_expenses(request.user)
    if _global_admin(request.user):
        payments = PaymentRecord.objects.filter(status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED])
    else:
        payments = PaymentRecord.objects.filter(order__in=orders, status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED])
    income = payments.aggregate(total=Sum('amount'))['total'] or 0
    expense_total = expenses_qs.filter(status=Expense.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0
    supplier_paid = SupplierPayment.objects.filter(
        purchase_order__in=purchase_orders, status=SupplierPayment.Status.PAID
    ).aggregate(total=Sum('amount'))['total'] or 0
    expenses = expense_total + supplier_paid
    receivable = sum((o.confirmed_price-_received(o) for o in orders), 0)
    supplier_due = sum((po.total-(po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0) for po in purchase_orders), 0)
    tx = _department_transactions(request.user).order_by('-transaction_date','-created_at')[:40]
    return JsonResponse({'stats':{'income':str(income),'expenses':str(expenses),'receivable':str(receivable),'supplier_due':str(supplier_due),'balance':str(income-expenses),'expense_count':expenses_qs.filter(status=Expense.Status.PAID).count()},'transactions':[_tx(x) for x in tx]})
@require_GET
@login_required
def expenses(request):
    _deny(request.user); q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=_department_expenses(request.user).select_related('category')
    if q: qs=qs.filter(Q(expense_no__icontains=q)|Q(category__name__icontains=q)|Q(description__icontains=q)|Q(reference__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'expenses':[_expense(x) for x in qs[:250]],'categories':[{'id':c.id,'name':c.name} for c in ExpenseCategory.objects.filter(is_active=True)],'statuses':_choices(Expense.Status.choices),'payment_methods':_choices([('cash','Cash'),('upi','UPI'),('bank','Bank Transfer'),('card','Card'),('other','Other')])})
@require_POST
@login_required
@transaction.atomic
def expense_create(request):
    _deny(request.user); _require_department(request.user); form=ExpenseForm(_data(request))
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    e=form.save(commit=False); e.created_by=request.user; e.save()
    if e.status==Expense.Status.PAID: FinanceTransaction.objects.create(transaction_type='expense',amount=e.amount,transaction_date=e.expense_date,payment_method=e.payment_method,reference=e.expense_no,description=e.description or e.category.name,expense=e,created_by=request.user)
    return JsonResponse({'expense':_expense(e)},status=201)
@require_POST
@login_required
def category_create(request):
    _deny(request.user); form=ExpenseCategoryForm(_data(request))
    if form.is_valid(): return JsonResponse({'category':{'id':form.save().id,'name':form.instance.name}},status=201)
    return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
@require_GET
@login_required
def receivables(request):
    _deny(request.user); rows=[]
    for o in _department_orders(request.user).select_related('customer').exclude(status=SalesOrder.Status.CANCELLED).prefetch_related('payments'):
        received=_received(o); balance=o.confirmed_price-received
        if balance>0: rows.append({'order':{'id':o.id,'order_no':o.order_no,'customer':o.customer.name,'total':str(o.confirmed_price)},'received':str(received),'balance':str(balance)})
    return JsonResponse({'rows':rows,'total':str(sum((Decimal(x['balance']) for x in rows), Decimal('0')))})
@require_GET
@login_required
def supplier_payments(request):
    _deny(request.user); payments=SupplierPayment.objects.filter(purchase_order__in=_department_purchase_orders(request.user)).select_related('purchase_order__supplier').order_by('-payment_date')[:150]; due=[]
    for po in _department_purchase_orders(request.user).select_related('supplier').exclude(status=PurchaseOrder.Status.CANCELLED):
        paid=po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0; balance=po.total-paid
        if balance>0: due.append({'order':{'id':po.id,'po_no':po.po_no,'supplier':po.supplier.name,'total':str(po.total)},'paid':str(paid),'balance':str(balance)})
    return JsonResponse({'payments':[_sp(x) for x in payments],'due':due,'total_due':str(sum((Decimal(x['balance']) for x in due), Decimal('0')))})
@require_POST
@login_required
@transaction.atomic
def supplier_payment_create(request):
    _deny(request.user); _require_department(request.user); form=SupplierPaymentForm(_data(request)); form.fields["purchase_order"].queryset = _department_purchase_orders(request.user).exclude(status=PurchaseOrder.Status.CANCELLED).select_related("supplier").order_by("-order_date")
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    p=form.save(commit=False)
    po=get_object_or_404(
        _department_purchase_orders(request.user).select_for_update(of=("self",)).exclude(status=PurchaseOrder.Status.CANCELLED),
        pk=p.purchase_order_id,
    )
    p.purchase_order=po
    paid=po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0
    balance=po.total-paid
    if p.status==SupplierPayment.Status.PAID and p.amount>balance: return JsonResponse({'detail':f'Payment cannot exceed current supplier balance of ₹ {balance:,.2f}.'},status=400)
    p.created_by=request.user; p.save()
    if p.status==SupplierPayment.Status.PAID: FinanceTransaction.objects.create(transaction_type='expense',amount=p.amount,transaction_date=p.payment_date,payment_method=p.payment_method,reference=p.payment_no,description=f'Supplier payment · {po.po_no} · {po.supplier.name}',supplier_payment=p,created_by=request.user)
    return JsonResponse({'payment':_sp(p)},status=201)
@require_GET
@login_required
def reconciliation(request):
    _deny(request.user); end=timezone.localdate(); start=end-timedelta(days=6)
    try:
        if request.GET.get('start'): start=date.fromisoformat(request.GET['start'])
        if request.GET.get('end'): end=date.fromisoformat(request.GET['end'])
    except ValueError: pass
    tx=_department_transactions(request.user).filter(status='posted',transaction_date__range=(start,end)); raw=tx.values('payment_method').annotate(income=Sum('amount',filter=Q(transaction_type='income')),expense=Sum('amount',filter=Q(transaction_type='expense')))
    by=[{'payment_method':r['payment_method'],'income':str(r['income'] or 0),'expense':str(r['expense'] or 0),'net':str((r['income'] or 0)-(r['expense'] or 0))} for r in raw]
    return JsonResponse({'start':start.isoformat(),'end':end.isoformat(),'by_method':by,'transactions':[_tx(x) for x in tx[:200]]})


def _founder(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(
        profile and profile.is_active and profile.role == UserProfile.Role.SUPER_ADMIN
    )


@require_GET
@login_required
def approval_thresholds(request):
    _deny(request.user)
    config = ApprovalThreshold.objects.order_by("pk").first()
    return JsonResponse({
        "purchase_amount": str(config.purchase_amount) if config and config.purchase_amount is not None else None,
        "expense_amount": str(config.expense_amount) if config and config.expense_amount is not None else None,
        "configured": bool(config and config.purchase_amount is not None and config.expense_amount is not None),
        "can_configure": _founder(request.user),
        "updated_at": config.updated_at.isoformat() if config else None,
    })


@require_POST
@login_required
@transaction.atomic
def approval_thresholds_update(request):
    if not _founder(request.user):
        return JsonResponse({"detail": "Only the Founder can configure purchase and expense approval thresholds."}, status=403)
    data = _data(request)
    values = {}
    for key in ("purchase_amount", "expense_amount"):
        raw = data.get(key)
        if raw in (None, ""):
            values[key] = None
            continue
        try:
            amount = Decimal(str(raw))
        except Exception:
            return JsonResponse({"detail": f"{key} must be a valid amount or blank."}, status=400)
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            return JsonResponse({"detail": f"{key} must be a non-negative amount with up to 2 decimal places."}, status=400)
        values[key] = amount
    config = ApprovalThreshold.objects.select_for_update().order_by("pk").first()
    if config is None:
        config = ApprovalThreshold.objects.create(**values, updated_by=request.user)
    else:
        for key, value in values.items():
            setattr(config, key, value)
        config.updated_by = request.user
        config.save(update_fields=["purchase_amount", "expense_amount", "updated_by", "updated_at"])
    from core.models import AuditLog
    AuditLog.objects.create(
        user=request.user, module="finance", action=AuditLog.Action.UPDATE,
        reference="approval-thresholds",
        description=f"Purchase threshold: {values['purchase_amount']}; Expense threshold: {values['expense_amount']}",
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return JsonResponse({"ok": True, "purchase_amount": str(config.purchase_amount) if config.purchase_amount is not None else None,
                         "expense_amount": str(config.expense_amount) if config.expense_amount is not None else None,
                         "updated_at": config.updated_at.isoformat()})
