from django import forms
from .models import QualityCheck, ReworkRecord, PackingRecord


class QualityCheckForm(forms.ModelForm):
    class Meta:
        model = QualityCheck
        fields = [
            "check_type", "result", "inspector", "stage",
            "design_match", "measurement_ok", "finishing_ok",
            "colour_ok", "engraving_ok", "cutting_ok", "assembly_ok",
            "sticking_ok", "polishing_ok", "electrical_ok", "appearance_ok", "packing_ok", "defects",
            "rework_reason", "corrective_action", "remarks",
        ]
        widgets = {
            "defects": forms.Textarea(attrs={"rows": 3}),
            "rework_reason": forms.Textarea(attrs={"rows": 3}),
            "corrective_action": forms.Textarea(attrs={"rows": 3}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("check_type") == QualityCheck.CheckType.FINAL
            and cleaned.get("result") == QualityCheck.Result.PASS
        ):
            checklist_fields = (
                "design_match", "measurement_ok", "cutting_ok", "assembly_ok",
                "sticking_ok", "finishing_ok", "polishing_ok", "colour_ok",
                "electrical_ok", "engraving_ok", "appearance_ok", "packing_ok",
            )
            incomplete = [
                self.fields[field].label or field.replace("_", " ").title()
                for field in checklist_fields
                if not cleaned.get(field)
            ]
            if incomplete:
                raise forms.ValidationError(
                    "Final QC cannot pass until every checklist item is confirmed: "
                    + ", ".join(incomplete)
                    + "."
                )
        return cleaned


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
