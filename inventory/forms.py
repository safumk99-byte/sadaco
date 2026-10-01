from django import forms
from products.models import Product
from production.models import ProductionMaterial
from .models import MaterialIssue, StockCount


class MaterialIssueForm(forms.ModelForm):
    class Meta:
        model = MaterialIssue
        fields = ["quantity", "reference", "remarks"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "reference": forms.TextInput(attrs={"placeholder": "Issue / job reference"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }


class StockCountForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(status=Product.Status.ACTIVE))
    counted_quantity = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "inventory-input")


class ReorderLevelForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["low_stock_threshold"]
        widgets = {"low_stock_threshold": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
