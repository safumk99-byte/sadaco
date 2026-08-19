from django.urls import path
from .views import (
    dashboard, job_detail, quality_create, rework_create,
    packing_update, quality_update, rework_update,
)

app_name = "quality"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("jobs/<int:pk>/", job_detail, name="job_detail"),
    path("jobs/<int:pk>/checks/add/", quality_create, name="quality_create"),
    path("checks/<int:pk>/edit/", quality_update, name="quality_update"),
    path("checks/<int:pk>/rework/add/", rework_create, name="rework_create"),
    path("rework/<int:pk>/edit/", rework_update, name="rework_update"),
    path("jobs/<int:pk>/packing/", packing_update, name="packing_update"),
]
