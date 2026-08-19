from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial=True
    dependencies=[
        ("sales","0004_link_requests_to_quotations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations=[
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("name",models.CharField(max_length=180)),("channel",models.CharField(max_length=80)),
                ("target_segment",models.CharField(blank=True,max_length=120)),("start_date",models.DateField(blank=True,null=True)),
                ("end_date",models.DateField(blank=True,null=True)),("budget",models.DecimalField(decimal_places=2,default=0,max_digits=12)),
                ("status",models.CharField(choices=[("planned","Planned"),("active","Active"),("completed","Completed"),("cancelled","Cancelled")],default="planned",max_length=20)),
                ("notes",models.TextField(blank=True)),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
                ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="marketing_campaigns",to=settings.AUTH_USER_MODEL)),
            ],options={"ordering":["-created_at"]},
        ),
        migrations.CreateModel(
            name="MarketingContent",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("title",models.CharField(max_length=180)),("channel",models.CharField(max_length=80)),
                ("content_date",models.DateField(blank=True,null=True)),("status",models.CharField(choices=[("idea","Idea"),("planned","Planned"),("published","Published")],default="idea",max_length=20)),
                ("content_url",models.URLField(blank=True)),("notes",models.TextField(blank=True)),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
                ("campaign",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="contents",to="marketing.campaign")),
                ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="marketing_contents",to=settings.AUTH_USER_MODEL)),
            ],options={"ordering":["-content_date","-created_at"]},
        ),
        migrations.CreateModel(
            name="MarketingLead",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("source",models.CharField(max_length=80)),("captured_on",models.DateField(default=django.utils.timezone.localdate)),
                ("status",models.CharField(choices=[("new","New"),("contacted","Contacted"),("converted","Converted"),("lost","Lost")],default="new",max_length=20)),
                ("notes",models.TextField(blank=True)),("created_at",models.DateTimeField(auto_now_add=True)),
                ("campaign",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="leads",to="marketing.campaign")),
                ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="marketing_leads_created",to=settings.AUTH_USER_MODEL)),
                ("customer",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="marketing_leads",to="sales.customer")),
                ("enquiry",models.OneToOneField(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="marketing_lead",to="sales.enquiry")),
            ],options={"ordering":["-captured_on","-created_at"]},
        ),
    ]
