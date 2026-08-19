import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Customer(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=180)
    phone = models.CharField(max_length=30)
    alternate_phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="customer_profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["phone"]), models.Index(fields=["status"]) ]

    def __str__(self):
        return self.name


class Enquiry(models.Model):
    class Channel(models.TextChoices):
        PHONE = "phone", "Phone"
        WHATSAPP = "whatsapp", "WhatsApp"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"
        WALK_IN = "walk_in", "Walk-in"
        REFERRAL = "referral", "Referral"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUOTATION = "quotation", "Quotation Prepared"
        CONVERTED = "converted", "Converted to Order"
        LOST = "lost", "Lost"

    enquiry_no = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="enquiries")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    product_type = models.CharField(max_length=180)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    design_reference = models.CharField(max_length=255, blank=True)
    deadline = models.DateField(null=True, blank=True)
    budget_range = models.CharField(max_length=120, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    requirement = models.TextField(blank=True)
    response_time_note = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales_enquiries",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_sales_enquiries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["customer", "status"]) ]

    def save(self, *args, **kwargs):
        if not self.enquiry_no:
            self.enquiry_no = f"ENQ-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.enquiry_no


class Quotation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CONVERTED = "converted", "Converted to Order"

    quotation_no = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotations")
    enquiry = models.ForeignKey(Enquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations")
    order_request = models.ForeignKey("OrderRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations")
    item_description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    material_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    labour_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    machine_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    finishing_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    packaging_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    delivery_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    quoted_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_timeline = models.CharField(max_length=180, blank=True)
    advance_required = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_quotations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"]), models.Index(fields=["customer", "status"]) ]

    @property
    def cost_total(self):
        return sum((self.material_cost, self.labour_cost, self.machine_cost, self.finishing_cost, self.packaging_cost, self.delivery_cost))

    def save(self, *args, **kwargs):
        if not self.quotation_no:
            self.quotation_no = f"QUO-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.quotation_no


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        DESIGN_PENDING = "design_pending", "Design Pending"
        PRODUCTION_PENDING = "production_pending", "Production Pending"
        IN_PRODUCTION = "in_production", "In Production"
        READY = "ready", "Ready"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order_no = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    quotation = models.ForeignKey(Quotation, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    item_description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    confirmed_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    design_reference = models.CharField(max_length=255, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    responsible_staff = models.ForeignKey("staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales_orders")
    advance_required = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.CONFIRMED)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_sales_orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "delivery_date"]), models.Index(fields=["customer", "status"]) ]

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_no


class OrderRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWING = "reviewing", "Under Review"
        CONTACTED = "contacted", "Customer Contacted"
        QUOTATION = "quotation", "Quotation in Progress"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    request_no = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="order_requests")
    request_type = models.CharField(max_length=20, choices=[("enquiry", "Enquiry"), ("order_request", "Order Request")], default="enquiry")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="customer_order_requests")
    product_name = models.CharField(max_length=180, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    size = models.CharField(max_length=120, blank=True)
    material_preference = models.CharField(max_length=180, blank=True)
    requirement = models.TextField()
    budget = models.CharField(max_length=120, blank=True)
    requested_date = models.DateField(null=True, blank=True)
    design_requirement = models.TextField(blank=True)
    reference_file = models.FileField(upload_to="customer_requests/%Y/%m/", blank=True, null=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    manager_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_customer_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["customer", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.request_no:
            self.request_no = f"REQ-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.request_no


class CustomerNotification(models.Model):
    class NotificationType(models.TextChoices):
        REQUEST = "request", "New Request"
        QUOTATION = "quotation", "Quotation"
        ORDER = "order", "Order"
        MESSAGE = "message", "Message"
        STATUS = "status", "Status Update"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_notifications")
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=180)
    message = models.TextField()
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
        ]

    def __str__(self):
        return self.title


class DesignApproval(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent to Customer"
        REVISION = "revision", "Revision Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="designs")
    version = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to="designs/%Y/%m/", blank=True, null=True)
    notes = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    sent_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_designs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["quotation", "version"], name="sales_design_quotation_version_uniq")
        ]

    def __str__(self):
        return f"{self.quotation.quotation_no} - Design v{self.version}"


class PaymentRecord(models.Model):
    class PaymentType(models.TextChoices):
        ADVANCE = "advance", "Advance"
        FINAL = "final", "Final"
        OTHER = "other", "Other"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        BANK = "bank", "Bank Transfer"
        CARD = "card", "Card"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RECEIVED = "received", "Received"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="payments")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    receipt_no = models.CharField(max_length=30, unique=True, editable=False, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    paid_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_sales_payments")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_no:
            self.receipt_no = f"REC-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_no} - {self.amount}"


class DeliveryRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SCHEDULED = "scheduled", "Scheduled"
        READY = "ready", "Ready for Delivery"
        OUT = "out", "Out for Delivery"
        DELIVERED = "delivered", "Delivered"
        INSTALLED = "installed", "Installed"
        CANCELLED = "cancelled", "Cancelled"

    order = models.OneToOneField(SalesOrder, on_delete=models.PROTECT, related_name="delivery")
    delivery_date = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    transport = models.CharField(max_length=120, blank=True)
    responsible_person = models.CharField(max_length=180, blank=True)
    installation_required = models.BooleanField(default=False)
    installation_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    acknowledgement = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order.order_no


class CustomerFeedback(models.Model):
    order = models.OneToOneField(SalesOrder, on_delete=models.PROTECT, related_name="feedback")
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback - {self.order.order_no}"


class CustomerInteraction(models.Model):
    class InteractionType(models.TextChoices):
        CALL = "call", "Phone Call"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        FOLLOW_UP = "follow_up", "Follow-up"
        NOTE = "note", "Note"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices, default=InteractionType.NOTE)
    subject = models.CharField(max_length=180)
    notes = models.TextField(blank=True)
    next_follow_up = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="customer_interactions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["next_follow_up", "completed"]),
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.subject}"
