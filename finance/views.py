from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

from accounts.decorators import role_required
from sales.models import Customer, PaymentRecord, SalesOrder
from purchase.models import PurchaseOrder
from .forms import ExpenseForm, ExpenseCategoryForm, CustomerPaymentForm, SupplierPaymentForm
from .models import Expense, ExpenseCategory, FinanceTransaction, SupplierPayment

manager_required = role_required("super_admin", "institution_admin", "manager")


def _received_total(order):
    return order.payments.filter(
        status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED]
    ).aggregate(total=Sum("amount"))["total"] or 0


@login_required
@manager_required
def dashboard(request):
    income = PaymentRecord.objects.filter(
        status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED]
    ).aggregate(total=Sum("amount"))["total"] or 0
    expenses = Expense.objects.filter(status=Expense.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
    receivable = sum((order.confirmed_price - _received_total(order) for order in SalesOrder.objects.exclude(status=SalesOrder.Status.CANCELLED)), 0)
    supplier_due = sum((po.total - (po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0)
                        for po in PurchaseOrder.objects.exclude(status=PurchaseOrder.Status.CANCELLED)), 0)
    transactions = FinanceTransaction.objects.select_related("expense", "sales_payment", "sales_payment__order").order_by("-transaction_date", "-created_at")[:40]
    return render(request, "finance/dashboard.html", {
        "title": "Finance & Accounts", "income": income, "expenses": expenses,
        "receivable": receivable, "balance": income - expenses,
        "supplier_due": supplier_due, "transactions": transactions,
        "expense_count": Expense.objects.filter(status=Expense.Status.PAID).count(),
    })


@login_required
@manager_required
@transaction.atomic
def expense_create(request):
    form = ExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.created_by = request.user
        expense.save()
        if expense.status == Expense.Status.PAID:
            FinanceTransaction.objects.create(
                transaction_type=FinanceTransaction.Type.EXPENSE,
                amount=expense.amount,
                transaction_date=expense.expense_date,
                payment_method=expense.payment_method,
                reference=expense.expense_no,
                description=expense.description or expense.category.name,
                expense=expense,
                created_by=request.user,
            )
        messages.success(request, f"Expense {expense.expense_no} recorded.")
        return redirect("finance:dashboard")
    return render(request, "finance/form.html", {"title": "Record Expense", "form": form, "back": "finance:dashboard"})


@login_required
@manager_required
def expense_category_create(request):
    form = ExpenseCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Expense category created.")
        return redirect("finance:dashboard")
    return render(request, "finance/form.html", {"title": "New Expense Category", "form": form, "back": "finance:dashboard"})


@login_required
@manager_required
@transaction.atomic
def payment_create(request, pk):
    order = get_object_or_404(SalesOrder.objects.select_related("customer"), pk=pk)
    form = CustomerPaymentForm(request.POST or None, order=order)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False)
        payment.order = order
        payment.created_by = request.user
        payment.save()
        if payment.status in (PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED):
            FinanceTransaction.objects.update_or_create(
                sales_payment=payment,
                defaults={
                    "transaction_type": FinanceTransaction.Type.INCOME,
                    "amount": payment.amount,
                    "transaction_date": payment.paid_on or timezone.localdate(),
                    "payment_method": payment.payment_method,
                    "reference": payment.receipt_no,
                    "description": f"{payment.get_payment_type_display()} payment · {order.order_no}",
                    "status": FinanceTransaction.Status.POSTED,
                    "created_by": request.user,
                },
            )
        if order.customer.user_id:
            from sales.models import CustomerNotification
            CustomerNotification.objects.create(
                user=order.customer.user,
                notification_type=CustomerNotification.NotificationType.STATUS,
                title=f"Payment updated for {order.order_no}",
                message=f"Payment of ₹ {payment.amount:,.2f} has been recorded.",
                url=f"/sales/portal/orders/{order.pk}/",
            )
        messages.success(request, f"Payment {payment.receipt_no} recorded successfully.")
        return redirect("sales:order_detail", pk=order.pk)
    return render(request, "finance/payment_form.html", {"title": f"Receive Payment · {order.order_no}", "form": form, "order": order})


@login_required
@manager_required
def receivables(request):
    orders = SalesOrder.objects.select_related("customer").exclude(status=SalesOrder.Status.CANCELLED).prefetch_related("payments")
    rows = []
    for order in orders:
        received = _received_total(order)
        balance = order.confirmed_price - received
        if balance > 0:
            rows.append({"order": order, "received": received, "balance": balance})
    return render(request, "finance/receivables.html", {"title": "Customer Receivables", "rows": rows, "total": sum((r["balance"] for r in rows), 0)})


@login_required
@manager_required
def supplier_payments(request):
    payments = SupplierPayment.objects.select_related("purchase_order__supplier", "created_by")[:100]
    due = []
    for po in PurchaseOrder.objects.select_related("supplier").exclude(status=PurchaseOrder.Status.CANCELLED):
        paid = po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
        balance = po.total - paid
        if balance > 0:
            due.append({"order": po, "paid": paid, "balance": balance})
    return render(request, "finance/supplier_payments.html", {"title": "Supplier Payments", "payments": payments, "due": due, "total_due": sum((x["balance"] for x in due), 0)})


@login_required
@manager_required
@transaction.atomic
def supplier_payment_create(request):
    form = SupplierPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False)
        po = payment.purchase_order
        paid = po.supplier_payments.filter(status=SupplierPayment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
        balance = po.total - paid
        if payment.status == SupplierPayment.Status.PAID and payment.amount > balance:
            form.add_error("amount", f"Payment cannot exceed the current supplier balance of ₹ {balance:,.2f}.")
        else:
            payment.created_by = request.user
            payment.save()
            if payment.status == SupplierPayment.Status.PAID:
                FinanceTransaction.objects.create(
                    transaction_type=FinanceTransaction.Type.EXPENSE,
                    amount=payment.amount,
                    transaction_date=payment.payment_date,
                    payment_method=payment.payment_method,
                    reference=payment.payment_no,
                    description=f"Supplier payment · {po.po_no} · {po.supplier.name}",
                    created_by=request.user,
                )
            messages.success(request, f"Supplier payment {payment.payment_no} recorded.")
            return redirect("finance:supplier_payments")
    return render(request, "finance/payment_form.html", {"title": "Supplier Payment", "form": form, "supplier_payment": True})


@login_required
@manager_required
def reconciliation(request):
    end = timezone.localdate()
    start = end - timedelta(days=6)
    try:
        if request.GET.get("start"):
            start = date.fromisoformat(request.GET["start"])
        if request.GET.get("end"):
            end = date.fromisoformat(request.GET["end"])
    except ValueError:
        messages.error(request, "Invalid reconciliation date range.")
    tx = FinanceTransaction.objects.filter(status=FinanceTransaction.Status.POSTED, transaction_date__range=(start, end))
    raw = tx.values("payment_method").annotate(
        income=Sum("amount", filter=Q(transaction_type=FinanceTransaction.Type.INCOME)),
        expense=Sum("amount", filter=Q(transaction_type=FinanceTransaction.Type.EXPENSE)),
    ).order_by("payment_method")
    by_method = []
    for row in raw:
        income = row["income"] or 0
        expense = row["expense"] or 0
        by_method.append({**row, "income": income, "expense": expense, "net": income - expense})
    return render(request, "finance/reconciliation.html", {"title": "Cash / UPI / Bank Reconciliation", "transactions": tx[:200], "by_method": by_method, "start": start, "end": end})
