from django.conf import settings
from django.db import models
from django.utils import timezone


class Campaign(models.Model):
    class Status(models.TextChoices):
        PLANNED="planned","Planned"
        ACTIVE="active","Active"
        COMPLETED="completed","Completed"
        CANCELLED="cancelled","Cancelled"

    name=models.CharField(max_length=180)
    channel=models.CharField(max_length=80)
    target_segment=models.CharField(max_length=120,blank=True)
    start_date=models.DateField(null=True,blank=True)
    end_date=models.DateField(null=True,blank=True)
    budget=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.PLANNED)
    notes=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="marketing_campaigns")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=["-created_at"]


class MarketingContent(models.Model):
    class Status(models.TextChoices):
        IDEA="idea","Idea"
        PLANNED="planned","Planned"
        PUBLISHED="published","Published"

    title=models.CharField(max_length=180)
    channel=models.CharField(max_length=80)
    campaign=models.ForeignKey(Campaign,on_delete=models.SET_NULL,null=True,blank=True,related_name="contents")
    content_date=models.DateField(null=True,blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.IDEA)
    content_url=models.URLField(blank=True)
    notes=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="marketing_contents")
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=["-content_date","-created_at"]


class MarketingLead(models.Model):
    class Status(models.TextChoices):
        NEW="new","New"
        CONTACTED="contacted","Contacted"
        CONVERTED="converted","Converted"
        LOST="lost","Lost"

    source=models.CharField(max_length=80)
    customer=models.ForeignKey("sales.Customer",on_delete=models.PROTECT,null=True,blank=True,related_name="marketing_leads")
    enquiry=models.OneToOneField("sales.Enquiry",on_delete=models.SET_NULL,null=True,blank=True,related_name="marketing_lead")
    campaign=models.ForeignKey(Campaign,on_delete=models.SET_NULL,null=True,blank=True,related_name="leads")
    captured_on=models.DateField(default=timezone.localdate)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.NEW)
    notes=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="marketing_leads_created")
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=["-captured_on","-created_at"]
