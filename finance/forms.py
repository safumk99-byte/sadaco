from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Sum

from .models import Expense, ExpenseCategory, SupplierPayment
from purchase.models import PurchaseOrder
from sales.models import PaymentRecord, SalesOrder

INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"

class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ["name", "is_active"]
        widgets = {"name": forms.TextInput(attrs={"class": INPUT}), "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4"})}

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["category", "amount", "expense_date", "payment_method", "reference", "description", "status"]
        widgets = {
            "category": forms.Select(attrs={"class": INPUT}), "amount": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0.01"}),
            "expense_date": forms.DateInput(attrs={"type": "date", "class": INPUT}), "payment_method": forms.Select(attrs={"class": INPUT}),
            "reference": forms.TextInput(attrs={"class": INPUT}), "description": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "status": forms.Select(attrs={"class": INPUT}),
        }

class CustomerPaymentForm(forms.ModelForm):
    class Meta:
        model = PaymentRecord
        fields = ["payment_type", "amount", "payment_method", "reference", "paid_on", "status", "notes"]
        widgets = {
            "payment_type": forms.Select(attrs={"class": INPUT}), "amount": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0.01"}),
            "payment_method": forms.Select(attrs={"class": INPUT}), "reference": forms.TextInput(attrs={"class": INPUT}),
            "paid_on": forms.DateInput(attrs={"type": "date", "class": INPUT}), "status": forms.Select(attrs={"class": INPUT}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
        }
    def __init__(self, *args, order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order
    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if not self.order:
            return amount
        received = self.order.payments.filter(status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED]).aggregate(total=Sum("amount"))["total"] or 0
        balance = self.order.confirmed_price - received
        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        if amount > balance:
            raise ValidationError(f"Payment cannot exceed the current balance of ₹ {balance:,.2f}.")
        return amount

class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = ["purchase_order", "amount", "payment_date", "payment_method", "reference", "status", "notes"]
        widgets = {
            "purchase_order": forms.Select(attrs={"class": INPUT}), "amount": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0.01"}),
            "payment_date": forms.DateInput(attrs={"type": "date", "class": INPUT}), "payment_method": forms.Select(attrs={"class": INPUT}),
            "reference": forms.TextInput(attrs={"class": INPUT}), "status": forms.Select(attrs={"class": INPUT}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["purchase_order"].queryset = PurchaseOrder.objects.exclude(status=PurchaseOrder.Status.CANCELLED).select_related("supplier").order_by("-order_date")
