from django.urls import path
from . import api
urlpatterns=[
 path('summary/',api.summary), path('suppliers/',api.suppliers), path('suppliers/create/',api.supplier_create),
 path('suppliers/<int:pk>/update/',api.supplier_update), path('orders/',api.orders), path('orders/create/',api.create),
 path('orders/<int:pk>/',api.detail), path('orders/<int:pk>/receive/',api.receive),
]
