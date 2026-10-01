from django.contrib import admin
from .models import Designation, PerformanceRecord, StaffAttendance, StaffProfile, StaffTask, WorkArea

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)

@admin.register(WorkArea)
class WorkAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("staff_id", "user", "designation", "work_area", "status", "joining_date")
    list_filter = ("status", "designation", "work_area")
    search_fields = ("staff_id", "user__username", "user__first_name", "user__last_name")

@admin.register(StaffTask)
class StaffTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assigned_to", "priority", "status", "due_date")
    list_filter = ("priority", "status")
    search_fields = ("title", "description")

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "status", "marked_by")
    list_filter = ("status", "date")
    search_fields = ("staff__staff_id", "staff__user__first_name", "staff__user__last_name")

@admin.register(PerformanceRecord)
class PerformanceRecordAdmin(admin.ModelAdmin):
    list_display = ("staff", "review_date", "score", "evaluator")
    list_filter = ("review_date", "score")
    search_fields = ("staff__staff_id", "staff__user__first_name", "staff__user__last_name")
