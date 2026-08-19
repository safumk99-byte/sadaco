from django import forms
from .models import ApprovalRequest

INPUT = "w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-400"


class ApprovalRequestForm(forms.ModelForm):
    class Meta:
        model = ApprovalRequest
        fields = ["module", "action", "reference", "amount", "reason"]
        widgets = {
            "module": forms.TextInput(attrs={"class": INPUT}),
            "action": forms.TextInput(attrs={"class": INPUT}),
            "reference": forms.TextInput(attrs={"class": INPUT}),
            "amount": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "reason": forms.Textarea(attrs={"class": INPUT, "rows": 4}),
        }


class ApprovalReviewForm(forms.ModelForm):
    class Meta:
        model = ApprovalRequest
        fields = ["status", "reviewer_note"]
        widgets = {
            "status": forms.Select(attrs={"class": INPUT}),
            "reviewer_note": forms.Textarea(attrs={"class": INPUT, "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (ApprovalRequest.Status.APPROVED, "Approve"),
            (ApprovalRequest.Status.REJECTED, "Reject"),
        ]
