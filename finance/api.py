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
from .models import Expense, ExpenseCategory, FinanceTransaction, SupplierPayment
MANAGER_ROLES={UserProfile.Role.SUPER_ADMIN,UserProfile.Role.INSTITUTION_ADMIN,UserProfile.Role.MANAGER}
def _manager(user): return user.is_superuser or getattr(getattr(user,'profile',None),'role',None) in MANAGER_ROLES
def _deny(user):
    if not _manager(user): raise PermissionDenied
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
    _deny(request.user); income=PaymentRecord.objects.filter(status__in=[PaymentRecord.Status.RECEIVED,PaymentRecord.Status.VERIFIED]).aggregate(total=Sum('amount'))['total'] or 0
    expenses=Expense.objects.filter(status=Expense.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0
    receivable=sum((o.confirmed_price-_received(o) for o in SalesOrder.objects.exclude(status=SalesOrder.Status.CANCELLED)),0)
    supplier_due=sum((po.total-(po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0) for po in PurchaseOrder.objects.exclude(status=PurchaseOrder.Status.CANCELLED)),0)
    tx=FinanceTransaction.objects.order_by('-transaction_date','-created_at')[:40]
    return JsonResponse({'stats':{'income':str(income),'expenses':str(expenses),'receivable':str(receivable),'supplier_due':str(supplier_due),'balance':str(income-expenses),'expense_count':Expense.objects.filter(status=Expense.Status.PAID).count()},'transactions':[_tx(x) for x in tx]})
@require_GET
@login_required
def expenses(request):
    _deny(request.user); q=request.GET.get('q','').strip(); status=request.GET.get('status',''); qs=Expense.objects.select_related('category')
    if q: qs=qs.filter(Q(expense_no__icontains=q)|Q(category__name__icontains=q)|Q(description__icontains=q)|Q(reference__icontains=q))
    if status: qs=qs.filter(status=status)
    return JsonResponse({'expenses':[_expense(x) for x in qs[:250]],'categories':[{'id':c.id,'name':c.name} for c in ExpenseCategory.objects.filter(is_active=True)],'statuses':_choices(Expense.Status.choices),'payment_methods':_choices([('cash','Cash'),('upi','UPI'),('bank','Bank Transfer'),('card','Card'),('other','Other')])})
@require_POST
@login_required
@transaction.atomic
def expense_create(request):
    _deny(request.user); form=ExpenseForm(_data(request))
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
    for o in SalesOrder.objects.select_related('customer').exclude(status=SalesOrder.Status.CANCELLED).prefetch_related('payments'):
        received=_received(o); balance=o.confirmed_price-received
        if balance>0: rows.append({'order':{'id':o.id,'order_no':o.order_no,'customer':o.customer.name,'total':str(o.confirmed_price)},'received':str(received),'balance':str(balance)})
    return JsonResponse({'rows':rows,'total':str(sum((Decimal(x['balance']) for x in rows), Decimal('0')))})
@require_GET
@login_required
def supplier_payments(request):
    _deny(request.user); payments=SupplierPayment.objects.select_related('purchase_order__supplier').order_by('-payment_date')[:150]; due=[]
    for po in PurchaseOrder.objects.select_related('supplier').exclude(status=PurchaseOrder.Status.CANCELLED):
        paid=po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0; balance=po.total-paid
        if balance>0: due.append({'order':{'id':po.id,'po_no':po.po_no,'supplier':po.supplier.name,'total':str(po.total)},'paid':str(paid),'balance':str(balance)})
    return JsonResponse({'payments':[_sp(x) for x in payments],'due':due,'total_due':str(sum((Decimal(x['balance']) for x in due), Decimal('0')))})
@require_POST
@login_required
@transaction.atomic
def supplier_payment_create(request):
    _deny(request.user); form=SupplierPaymentForm(_data(request))
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    p=form.save(commit=False); po=p.purchase_order; paid=po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum('amount'))['total'] or 0; balance=po.total-paid
    if p.status==SupplierPayment.Status.PAID and p.amount>balance: return JsonResponse({'detail':f'Payment cannot exceed current supplier balance of ₹ {balance:,.2f}.'},status=400)
    p.created_by=request.user; p.save()
    if p.status==SupplierPayment.Status.PAID: FinanceTransaction.objects.create(transaction_type='expense',amount=p.amount,transaction_date=p.payment_date,payment_method=p.payment_method,reference=p.payment_no,description=f'Supplier payment · {po.po_no} · {po.supplier.name}',created_by=request.user)
    return JsonResponse({'payment':_sp(p)},status=201)
@require_GET
@login_required
def reconciliation(request):
    _deny(request.user); end=timezone.localdate(); start=end-timedelta(days=6)
    try:
        if request.GET.get('start'): start=date.fromisoformat(request.GET['start'])
        if request.GET.get('end'): end=date.fromisoformat(request.GET['end'])
    except ValueError: pass
    tx=FinanceTransaction.objects.filter(status='posted',transaction_date__range=(start,end)); raw=tx.values('payment_method').annotate(income=Sum('amount',filter=Q(transaction_type='income')),expense=Sum('amount',filter=Q(transaction_type='expense')))
    by=[{'payment_method':r['payment_method'],'income':str(r['income'] or 0),'expense':str(r['expense'] or 0),'net':str((r['income'] or 0)-(r['expense'] or 0))} for r in raw]
    return JsonResponse({'start':start.isoformat(),'end':end.isoformat(),'by_method':by,'transactions':[_tx(x) for x in tx[:200]]})
