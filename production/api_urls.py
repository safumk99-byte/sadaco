from django.urls import path
from .api import summary, jobs, options, detail, create, update, add_progress, add_material, add_issue, add_cost_entry
urlpatterns = [
    path("summary/", summary), path("jobs/", jobs), path("options/", options), path("jobs/<int:pk>/", detail),
    path("jobs/create/", create), path("jobs/<int:pk>/update/", update), path("jobs/<int:pk>/progress/", add_progress),
    path("jobs/<int:pk>/materials/", add_material), path("jobs/<int:pk>/issues/", add_issue),
    path("jobs/<int:pk>/cost-entries/", add_cost_entry),\n    path("jobs/<int:pk>/stage-tasks/", __import__("production.api", fromlist=["upsert_stage_task"]).upsert_stage_task),
]
