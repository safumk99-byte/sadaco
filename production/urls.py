from django.urls import path
from .views import dashboard, job_list, job_create, job_detail, job_update, progress_add, material_add, issue_add
app_name="production"
urlpatterns=[
 path("",dashboard,name="dashboard"),
 path("jobs/",job_list,name="jobs"),
 path("orders/<int:order_pk>/create/",job_create,name="job_create"),
 path("jobs/<int:pk>/",job_detail,name="job_detail"),
 path("jobs/<int:pk>/edit/",job_update,name="job_update"),
 path("jobs/<int:pk>/progress/",progress_add,name="progress_add"),
 path("jobs/<int:pk>/materials/add/",material_add,name="material_add"),
 path("jobs/<int:pk>/issues/add/",issue_add,name="issue_add"),
]
