from django.urls import path
from . import api

urlpatterns = [
    path("materials/stock/", api.material_stock_api, name="material_stock"),
    path("materials/movements/", api.material_movements_api, name="material_movements"),
    path("materials/movements/create/", api.material_movement_create_api, name="material_movement_create"),
    path("materials/options/", api.material_options_api, name="material_options"),
    path("materials/balances/create/", api.material_balance_create_api, name="material_balance_create"),
    path("materials/offcuts/", api.offcuts_api, name="material_offcuts"),
]
