from django.urls import path
from .api_views import dashboard
urlpatterns=[path('dashboard/',dashboard)]
