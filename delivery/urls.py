from django.urls import path
from .views import dashboard, delivery_detail, delivery_update, feedback_create

app_name="delivery"
urlpatterns=[
    path("",dashboard,name="dashboard"),
    path("orders/<int:pk>/",delivery_detail,name="detail"),
    path("orders/<int:pk>/update/",delivery_update,name="update"),
    path("orders/<int:pk>/feedback/",feedback_create,name="feedback"),
]
