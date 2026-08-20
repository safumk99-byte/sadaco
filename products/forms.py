from django import forms
from django.db import models

from .models import Product, ProductCategory, StockTransaction

INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-400"


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "is_active": forms.CheckboxInput(),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "sku", "category", "description", "unit",
            "selling_price", "actual_price", "discount_price",
            "customer_visible", "image",
            "cost_price", "stock_quantity", "low_stock_threshold", "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "sku": forms.TextInput(attrs={"class": INPUT}),
            "category": forms.Select(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
            "unit": forms.TextInput(attrs={"class": INPUT}),
            "selling_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "actual_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "discount_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "customer_visible": forms.CheckboxInput(),
            "image": forms.ClearableFileInput(attrs={"class": INPUT, "accept": "image/jpeg,image/png,image/webp"}),
            "cost_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "stock_quantity": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "low_stock_threshold": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "status": forms.Select(attrs={"class": INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = ProductCategory.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.category_id:
            active = ProductCategory.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.category_id)
            )
        self.fields["category"].queryset = active

    def clean_sku(self):
        return self.cleaned_data["sku"].strip().upper()

    def clean(self):
        cleaned = super().clean()
        actual = cleaned.get("actual_price")
        discount = cleaned.get("discount_price")

        if actual is not None and actual <= 0:
            self.add_error("actual_price", "Actual price must be greater than zero.")

        if actual is not None and discount is not None and discount > actual:
            self.add_error(
                "discount_price",
                "Discount price cannot be higher than actual price.",
            )

        return cleaned


class StockTransactionForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(status=Product.Status.ACTIVE),
        widget=forms.Select(attrs={"class": INPUT}),
    )
    transaction_type = forms.ChoiceField(
        choices=StockTransaction.TransactionType.choices,
        widget=forms.Select(attrs={"class": INPUT}),
    )
    quantity = forms.DecimalField(
        min_value=0,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
    )
    reference = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "Invoice / reference number"}),
    )
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT, "rows": 3}),
    )
