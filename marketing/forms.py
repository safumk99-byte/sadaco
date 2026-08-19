from django import forms
from .models import Campaign, MarketingContent, MarketingLead

class CampaignForm(forms.ModelForm):
    class Meta:
        model=Campaign
        fields=["name","channel","target_segment","start_date","end_date","budget","status","notes"]
        widgets={"start_date":forms.DateInput(attrs={"type":"date"}),"end_date":forms.DateInput(attrs={"type":"date"}),"notes":forms.Textarea(attrs={"rows":3})}

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
