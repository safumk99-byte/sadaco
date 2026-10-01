from django.urls import path
from . import api
urlpatterns=[path('dashboard/',api.dashboard),path('expenses/',api.expenses),path('expenses/create/',api.expense_create),path('categories/create/',api.category_create),path('receivables/',api.receivables),path('supplier-payments/',api.supplier_payments),path('supplier-payments/create/',api.supplier_payment_create),path('reconciliation/',api.reconciliation)]
