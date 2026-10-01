from django.urls import path
from .api import summary, checks, options, detail, create_check, update_check, create_rework, update_rework, update_packing
urlpatterns = [
    path("summary/", summary), path("checks/", checks), path("options/", options), path("jobs/<int:pk>/", detail),
    path("checks/create/", create_check), path("checks/<int:pk>/update/", update_check), path("checks/<int:check_id>/rework/", create_rework),
    path("rework/<int:pk>/update/", update_rework), path("jobs/<int:pk>/packing/", update_packing),
]
