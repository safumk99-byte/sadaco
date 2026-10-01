from django.urls import path
from .api import summary, jobs, options, detail, create, update, add_progress, add_material, add_issue
urlpatterns = [
    path("summary/", summary), path("jobs/", jobs), path("options/", options), path("jobs/<int:pk>/", detail),
    path("jobs/create/", create), path("jobs/<int:pk>/update/", update), path("jobs/<int:pk>/progress/", add_progress),
    path("jobs/<int:pk>/materials/", add_material), path("jobs/<int:pk>/issues/", add_issue),
]
