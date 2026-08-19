from django.urls import path
from .views import (
    dashboard, expense_create, expense_category_create, payment_create,
    receivables, supplier_payments, supplier_payment_create, reconciliation,
)

app_name = "finance"
urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("expenses/add/", expense_create, name="expense_create"),
    path("expense-categories/add/", expense_category_create, name="expense_category_create"),
    path("payments/order/<int:pk>/add/", payment_create, name="payment_create"),
    path("receivables/", receivables, name="receivables"),
    path("supplier-payments/", supplier_payments, name="supplier_payments"),
    path("supplier-payments/add/", supplier_payment_create, name="supplier_payment_create"),
    path("reconciliation/", reconciliation, name="reconciliation"),
]
