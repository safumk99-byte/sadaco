from django.contrib import admin
from . import models

for model in [
    models.Division, models.Department, models.StaffProfile, models.Role,
    models.Permission, models.RolePermission, models.StaffRole,
    models.StaffDepartment, models.StaffDivision, models.Customer,
    models.Enquiry, models.FollowUp, models.CustomerCommunication,
    models.ApprovalRequest, models.Quotation, models.QuotationItem,
    models.SalesOrder, models.OrderItem, models.OrderAssignment,
    models.OrderStatusEvent, models.DesignRecord, models.DesignRevision,
    models.StoredFile, models.DesignRevisionFile,
    models.JobCard, models.ProductionStage, models.ProductionUpdate,
    models.StaffTask, models.TaskUpdate, models.AuditEvent,
]:
    admin.site.register(model)


@admin.register(models.DesignApproval)
class DesignApprovalAdmin(admin.ModelAdmin):
    list_display = ("design_revision", "reviewer_type", "decision", "reviewed_by", "reviewed_at")
    list_filter = ("reviewer_type", "decision")
    search_fields = ("design_revision__design_record__title", "comments")
    readonly_fields = (
        "design_revision", "reviewer_type", "decision",
        "reviewed_by", "reviewed_at", "comments",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
