from django import forms
from .models import Campaign, MarketingContent, MarketingLead
from django.core.exceptions import ValidationError

class CampaignForm(forms.ModelForm):
    class Meta:
        model=Campaign
        fields=["name","channel","target_segment","start_date","end_date","budget","status","notes"]
        widgets={"start_date":forms.DateInput(attrs={"type":"date"}),"end_date":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "Campaign end date cannot be before its start date.")
        budget = cleaned.get("budget")
        if budget is not None and budget < 0:
            self.add_error("budget", "Campaign budget cannot be negative.")
        return cleaned

class ContentForm(forms.ModelForm):
    class Meta:
        model=MarketingContent
        fields=["title","channel","campaign","content_date","status","content_url","notes"]
        widgets={"content_date":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}

class LeadForm(forms.ModelForm):
    class Meta:
        model=MarketingLead
        fields=["source","customer","enquiry","campaign","captured_on","status","notes"]
        widgets={"captured_on":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}

    def clean(self):
        cleaned = super().clean()
        customer = cleaned.get("customer")
        enquiry = cleaned.get("enquiry")
        if customer and enquiry and enquiry.customer_id != customer.pk:
            self.add_error("enquiry", "Selected enquiry belongs to a different customer.")
        return cleaned
