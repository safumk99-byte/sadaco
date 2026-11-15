from django.urls import path
from . import api

urlpatterns = [
    path("materials/stock/", api.material_stock_api, name="material_stock"),
    path("materials/lots/", api.material_stock_lots_api, name="material_stock_lots"),
    path("materials/movements/", api.material_movements_api, name="material_movements"),
    path("materials/movements/create/", api.material_movement_create_api, name="material_movement_create"),
    path("materials/options/", api.material_options_api, name="material_options"),
    path("materials/balances/create/", api.material_balance_create_api, name="material_balance_create"),
    path("materials/offcuts/", api.offcuts_api, name="material_offcuts"),
    path("materials/offcuts/create/", api.offcut_create_api, name="material_offcut_create"),
    path("materials/offcuts/<int:pk>/action/", api.offcut_action_api, name="material_offcut_action"),
    path("materials/issues/create/", api.production_material_issue_api, name="production_material_issue"),
    path("materials/returns/create/", api.production_material_return_api, name="production_material_return"),
    path("materials/wastage/create/", api.production_material_wastage_api, name="production_material_wastage"),
    path("materials/stock-counts/", api.material_stock_counts_api, name="material_stock_counts"),
    path("materials/stock-counts/submit/", api.material_stock_count_submit_api, name="material_stock_count_submit"),
    path("materials/stock-counts/<int:pk>/review/", api.material_stock_count_review_api, name="material_stock_count_review"),
]
