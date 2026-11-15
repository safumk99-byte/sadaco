from django.contrib import admin

from .models import AuditLog, ApprovalRequest, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "manager", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "manager__username", "manager__first_name", "manager__last_name")
    autocomplete_fields = ("manager",)


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("module", "action", "reference", "amount", "status", "requested_by", "created_at")
    list_filter = ("module", "status")
    search_fields = ("module", "action", "reference", "reason")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("module", "action", "reference", "user", "created_at")
    list_filter = ("module", "action")
    search_fields = ("module", "reference", "description", "user__username")
