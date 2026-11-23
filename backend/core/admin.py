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
    models.StoredFile, models.DesignRevisionFile, models.DesignApproval,
    models.JobCard, models.ProductionStage, models.ProductionUpdate,
    models.StaffTask, models.TaskUpdate, models.AuditEvent,
]:
    admin.site.register(model)
