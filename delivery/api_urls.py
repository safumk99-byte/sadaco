from django.urls import path
from .api_views import summary, detail, update, feedback
urlpatterns=[path('summary/',summary),path('orders/<int:pk>/',detail),path('orders/<int:pk>/update/',update),path('orders/<int:pk>/feedback/',feedback)]
