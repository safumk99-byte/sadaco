from django.urls import path
from .api_views import summary, detail, update, feedback, close_order
urlpatterns=[path('summary/',summary),path('orders/<int:pk>/',detail),path('orders/<int:pk>/update/',update),path('orders/<int:pk>/feedback/',feedback),path('orders/<int:pk>/close/',close_order)]
