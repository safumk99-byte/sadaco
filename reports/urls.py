from django.urls import path
from .views import dashboard, export_csv, export_pdf

app_name = "reports"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("export.csv", export_csv, name="export_csv"),
    path("export.pdf", export_pdf, name="export_pdf"),
]
