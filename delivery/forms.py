from django import forms
from sales.models import DeliveryRecord, CustomerFeedback

class DeliveryForm(forms.ModelForm):
    class Meta:
        model=DeliveryRecord
        fields=["delivery_date","address","transport","responsible_person","installation_required","installation_date","status","acknowledgement","completion_notes"]
        widgets={
            "delivery_date":forms.DateInput(attrs={"type":"date"}),
            "installation_date":forms.DateInput(attrs={"type":"date"}),
            "acknowledgement":forms.Textarea(attrs={"rows":3}),
            "completion_notes":forms.Textarea(attrs={"rows":3}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model=CustomerFeedback
        fields=["rating","comment"]
        widgets={"rating":forms.NumberInput(attrs={"min":"1","max":"5"}),"comment":forms.Textarea(attrs={"rows":4})}
