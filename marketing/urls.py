from django.urls import path
from .views import dashboard,campaign_create,content_create,lead_create

app_name="marketing"
urlpatterns=[
 path("",dashboard,name="dashboard"),
 path("campaigns/add/",campaign_create,name="campaign_create"),
 path("content/add/",content_create,name="content_create"),
 path("leads/add/",lead_create,name="lead_create"),
]
