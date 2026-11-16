from django import forms
from .models import ProductionJob, ProductionProgress, ProductionMaterial, ProductionIssue

class ProductionJobForm(forms.ModelForm):
    class Meta:
        model = ProductionJob
        fields = ["station","stage","status","assigned_staff","priority","deadline","safety_checked","design_checked","material_ready","notes"]
        widgets = {"deadline": forms.DateInput(attrs={"type":"date"}), "notes": forms.Textarea(attrs={"rows":4})}

class ProductionProgressForm(forms.ModelForm):
    class Meta:
        model = ProductionProgress
        fields = ["stage","progress_percent","note"]
        widgets = {"progress_percent": forms.NumberInput(attrs={"min":0,"max":100}), "note": forms.Textarea(attrs={"rows":3})}

    def clean_progress_percent(self):
        value = self.cleaned_data["progress_percent"]
        if value < 0 or value > 100:
            raise forms.ValidationError("Progress must be between 0 and 100.")
        return value

class ProductionMaterialForm(forms.ModelForm):
    class Meta:
        model = ProductionMaterial
        fields = ["product","material_variant","material_name","quantity_required","unit","notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows":2})}

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        material_variant = cleaned.get("material_variant")
        if product and material_variant:
            raise forms.ValidationError("Select either a finished product or a Material Master item, not both.")
        if material_variant:
            cleaned["material_name"] = material_variant.material_name
            cleaned["unit"] = material_variant.unit
        return cleaned

class ProductionIssueForm(forms.ModelForm):
    class Meta:
        model = ProductionIssue
        fields = ["issue_type","stage","reason","corrective_action","staff"]
        widgets = {"reason":forms.Textarea(attrs={"rows":3}),"corrective_action":forms.Textarea(attrs={"rows":3})}
