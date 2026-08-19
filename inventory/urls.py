from django.urls import path
from .views import dashboard, issue_create, stock_count_create, reorder_list

app_name = "inventory"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("issue/<int:material_id>/", issue_create, name="issue_material"),
    path("stock-count/", stock_count_create, name="stock_count"),
    path("reorder/", reorder_list, name="reorder"),
]
