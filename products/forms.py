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
            "cost_price", "stock_quantity", "low_stock_threshold",
        ]
        labels = {
            "name": "Product / Material Name",
            "sku": "SKU / Code",
            "category": "Category",
            "description": "Description",
            "unit": "Unit",
            "cost_price": "Cost Price",
            "stock_quantity": "Current / Opening Stock",
            "low_stock_threshold": "Low Stock Threshold",
        }
        help_texts = {
            "cost_price": "Internal cost of one unit. Customer selling price is managed separately in the customer catalogue.",
            "stock_quantity": "Enter the current quantity when adding an existing item, or the opening quantity for a new item.",
            "low_stock_threshold": "The system can use this level to flag low-stock items.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. 5mm Acrylic Sheet"}),
            "sku": forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. MAT-ACR-005"}),
            "category": forms.Select(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3, "placeholder": "Internal product/material description"}),
            "unit": forms.TextInput(attrs={"class": INPUT, "placeholder": "Piece, Sheet, Meter, Kg..."}),
            "cost_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0", "placeholder": "0.00"}),
            "stock_quantity": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0", "placeholder": "0"}),
            "low_stock_threshold": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0", "placeholder": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Internal products use top-level internal categories only.
        active = ProductCategory.objects.filter(
            is_active=True, parent__isnull=True, is_section=False
        )
        if self.instance and self.instance.pk and self.instance.category_id:
            active = ProductCategory.objects.filter(
                models.Q(is_active=True, parent__isnull=True, is_section=False)
                | models.Q(pk=self.instance.category_id)
            )
        self.fields["category"].queryset = active

    def clean_sku(self):
        return self.cleaned_data["sku"].strip().upper()

    def save(self, commit=True):
        product = super().save(commit=False)
        # Internal product records must never enter the customer catalogue.
        product.selling_price = 0
        product.actual_price = 0
        product.discount_price = 0
        product.customer_visible = False
        if commit:
            product.save()
            self.save_m2m()
        return product


class StockTransactionForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(status=Product.Status.ACTIVE, customer_visible=False),
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


class CatalogSectionForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "Section name"}),
        }


class CatalogCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ["name", "parent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "Category name"}),
            "parent": forms.Select(attrs={"class": INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = ProductCategory.objects.filter(
            parent__isnull=True, is_section=True, is_active=True
        ).exclude(name__iexact="WHITE ELEGANCE").order_by("name")
        self.fields["parent"].required = True
        self.fields["parent"].empty_label = "Select section"
        self.fields["parent"].label = "Section"


class CatalogProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "description", "actual_price", "discount_price", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "Product name"}),
            "category": forms.Select(attrs={"class": INPUT}),
            "description": forms.Textarea(attrs={"class": INPUT, "rows": 3, "placeholder": "Short product description"}),
            "actual_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0", "placeholder": "0.00"}),
            "discount_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0", "placeholder": "Optional"}),
            "image": forms.ClearableFileInput(attrs={"class": INPUT, "accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ProductCategory.objects.filter(
            is_active=True, parent__isnull=False
        ).select_related("parent").order_by("parent__name", "name")
        self.fields["category"].label = "Category"
        self.fields["category"].label_from_instance = lambda obj: f"{obj.parent.name} → {obj.name}"
        self.fields["actual_price"].label = "Price"
        self.fields["discount_price"].label = "Offer price"

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get("actual_price")
        offer = cleaned.get("discount_price")
        if price is not None and price <= 0:
            self.add_error("actual_price", "Price must be greater than zero.")
        if price is not None and offer is not None and offer > 0 and offer > price:
            self.add_error("discount_price", "Offer price cannot be higher than price.")
        return cleaned
