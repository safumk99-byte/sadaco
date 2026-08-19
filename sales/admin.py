from django.contrib import admin

from .models import Customer, CustomerFeedback, CustomerNotification, DeliveryRecord, DesignApproval, Enquiry, OrderRequest, PaymentRecord, Quotation, SalesOrder


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "status", "created_at")
    search_fields = ("name", "phone", "email")
    list_filter = ("status",)


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("enquiry_no", "customer", "product_type", "status", "channel", "created_at")
    search_fields = ("enquiry_no", "customer__name", "product_type")
    list_filter = ("status", "channel")


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("quotation_no", "customer", "quoted_price", "status", "valid_until", "created_at")
    search_fields = ("quotation_no", "customer__name", "item_description")
    list_filter = ("status",)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "customer", "confirmed_price", "status", "delivery_date", "created_at")
    search_fields = ("order_no", "customer__name", "item_description")
    list_filter = ("status",)


@admin.register(OrderRequest)
class OrderRequestAdmin(admin.ModelAdmin):
    list_display = ("request_no", "customer", "request_type", "status", "assigned_to", "created_at")
    list_filter = ("request_type", "status")
    search_fields = ("request_no", "customer__name", "product_name", "requirement")
    readonly_fields = ("request_no", "created_at", "updated_at")


@admin.register(CustomerNotification)
class CustomerNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "message", "user__username")


@admin.register(DesignApproval)
class DesignApprovalAdmin(admin.ModelAdmin):
    list_display = ("quotation", "version", "status", "sent_at", "responded_at")
    list_filter = ("status",)
    search_fields = ("quotation__quotation_no", "quotation__customer__name")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("order", "payment_type", "amount", "status", "paid_on", "created_at")
    list_filter = ("payment_type", "status")
    search_fields = ("order__order_no", "reference")


@admin.register(DeliveryRecord)
class DeliveryRecordAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "delivery_date", "installation_required")
    list_filter = ("status", "installation_required")
    search_fields = ("order__order_no", "transport", "responsible_person")


@admin.register(CustomerFeedback)
class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = ("order", "rating", "submitted_at")
    list_filter = ("rating",)
    search_fields = ("order__order_no", "comment")
