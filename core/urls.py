from django.urls import path
from .views import (
    dashboard, health_check,
    approval_list, approval_create, approval_review, audit_log,
)

app_name = "core"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("health/", health_check, name="health"),
    path("approvals/", approval_list, name="approvals"),
    path("approvals/create/", approval_create, name="approval_create"),
    path("approvals/<int:pk>/review/", approval_review, name="approval_review"),
    path("audit-log/", audit_log, name="audit_log"),
]
