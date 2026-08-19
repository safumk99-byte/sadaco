from django import forms
from .models import QualityCheck, ReworkRecord, PackingRecord


class QualityCheckForm(forms.ModelForm):
    class Meta:
        model = QualityCheck
        fields = [
            "check_type", "result", "inspector", "stage",
            "design_match", "measurement_ok", "finishing_ok",
            "colour_ok", "engraving_ok", "defects",
            "rework_reason", "corrective_action", "remarks",
        ]
        widgets = {
            "defects": forms.Textarea(attrs={"rows": 3}),
            "rework_reason": forms.Textarea(attrs={"rows": 3}),
            "corrective_action": forms.Textarea(attrs={"rows": 3}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }


class ReworkRecordForm(forms.ModelForm):
    class Meta:
        model = ReworkRecord
        fields = ["reason", "corrective_action", "assigned_staff", "due_date", "status"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3}),
            "corrective_action": forms.Textarea(attrs={"rows": 3}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class PackingRecordForm(forms.ModelForm):
    class Meta:
        model = PackingRecord
        fields = ["packing_material", "fragile_protection", "customer_label", "status", "packed_by", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
