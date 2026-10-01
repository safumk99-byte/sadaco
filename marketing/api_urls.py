from django.urls import path
from .api_views import dashboard,campaign_create,content_create,lead_create
urlpatterns=[path('dashboard/',dashboard),path('campaigns/create/',campaign_create),path('content/create/',content_create),path('leads/create/',lead_create)]
