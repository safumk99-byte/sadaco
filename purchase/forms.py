from django import forms
from .models import Supplier, PurchaseOrder, PurchaseItem, GoodsReceipt

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name","contact_person","phone","email","address","tax_number","payment_terms","notes","status"]

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier","order_date","expected_date","status","discount","tax","notes"]
        widgets = {"order_date":forms.DateInput(attrs={"type":"date"}),"expected_date":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}

class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ["product","quantity","unit_cost","notes"]
        widgets = {"quantity":forms.NumberInput(attrs={"step":"0.01","min":"0.01"}),"unit_cost":forms.NumberInput(attrs={"step":"0.01","min":"0"})}

class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ["received_date","supplier_reference","notes"]
        widgets = {"received_date":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}
