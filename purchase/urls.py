from django.urls import path
from .views import dashboard, supplier_list, supplier_create, purchase_create, purchase_detail, receive_purchase

app_name="purchase"
urlpatterns=[
    path("", dashboard, name="dashboard"),
    path("suppliers/", supplier_list, name="suppliers"),
    path("suppliers/add/", supplier_create, name="supplier_create"),
    path("orders/add/", purchase_create, name="purchase_create"),
    path("orders/<int:pk>/", purchase_detail, name="purchase_detail"),
    path("orders/<int:pk>/receive/", receive_purchase, name="receive_purchase"),
]
