from django.urls import path

from .views import (
    attendance_create, attendance_list,
    designation_create, designation_edit, designation_list,
    performance_create, performance_list,
    staff_create, staff_detail, staff_edit, staff_list,
    task_create, task_edit, task_list,
    work_area_create, work_area_edit, work_area_list,
)

app_name = "staff"

urlpatterns = [
    path("", staff_list, name="list"),
    path("create/", staff_create, name="create"),
    path("<int:pk>/", staff_detail, name="detail"),
    path("<int:pk>/edit/", staff_edit, name="edit"),
    path("designations/", designation_list, name="designations"),
    path("designations/create/", designation_create, name="designation_create"),
    path("designations/<int:pk>/edit/", designation_edit, name="designation_edit"),
    path("work-areas/", work_area_list, name="work_areas"),
    path("work-areas/create/", work_area_create, name="work_area_create"),
    path("work-areas/<int:pk>/edit/", work_area_edit, name="work_area_edit"),
    path("tasks/", task_list, name="tasks"),
    path("tasks/create/", task_create, name="task_create"),
    path("tasks/<int:pk>/edit/", task_edit, name="task_edit"),
    path("attendance/", attendance_list, name="attendance"),
    path("attendance/create/", attendance_create, name="attendance_create"),
    path("performance/", performance_list, name="performance"),
    path("performance/create/", performance_create, name="performance_create"),
]
