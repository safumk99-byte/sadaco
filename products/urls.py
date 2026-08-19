from django.urls import path

from .views import (
    category_create, category_edit, category_list,
    product_create, product_detail, product_edit, product_list, stock_list, stock_transaction_create,
)

app_name = "products"

urlpatterns = [
    path("", product_list, name="list"),
    path("create/", product_create, name="create"),
    path("<int:pk>/", product_detail, name="detail"),
    path("<int:pk>/edit/", product_edit, name="edit"),
    path("stock/", stock_list, name="stock"),
    path("stock/transaction/", stock_transaction_create, name="stock_transaction"),
    path("categories/", category_list, name="categories"),
    path("categories/create/", category_create, name="category_create"),
    path("categories/<int:pk>/edit/", category_edit, name="category_edit"),
]
