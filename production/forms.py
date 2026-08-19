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

class ProductionMaterialForm(forms.ModelForm):
    class Meta:
        model = ProductionMaterial
        fields = ["product","material_name","quantity_required","unit","issued_quantity","notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows":2})}

class ProductionIssueForm(forms.ModelForm):
    class Meta:
        model = ProductionIssue
        fields = ["issue_type","stage","reason","corrective_action","staff"]
        widgets = {"reason":forms.Textarea(attrs={"rows":3}),"corrective_action":forms.Textarea(attrs={"rows":3})}
