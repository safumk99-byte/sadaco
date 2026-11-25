import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Division(UUIDModel, TimeStampedModel):
    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(UUIDModel, TimeStampedModel):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["division__name", "name"]
        constraints = [models.UniqueConstraint(fields=["division", "name"], name="uq_department_division_name")]

    def __str__(self):
        return f"{self.division.code} / {self.name}"


class StaffProfile(UUIDModel, TimeStampedModel):
    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staff_profile")
    display_name = models.CharField(max_length=180)
    mobile = models.CharField(max_length=30, blank=True)
    employment_status = models.CharField(max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE)
    departments = models.ManyToManyField(Department, through="StaffDepartment", related_name="staff_members")
    divisions = models.ManyToManyField(Division, through="StaffDivision", related_name="staff_members")

    def __str__(self):
        return self.display_name


class Role(UUIDModel, TimeStampedModel):
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField("Permission", through="RolePermission", related_name="roles")

    def __str__(self):
        return self.name


class Permission(UUIDModel):
    code = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=240)

    def __str__(self):
        return self.code


class RolePermission(UUIDModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["role", "permission"], name="uq_role_permission")]


class StaffRole(UUIDModel, TimeStampedModel):
    staff = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="staff_assignments")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    granted_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="granted_roles")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(valid_until__isnull=True) | Q(valid_until__gt=models.F("valid_from")), name="ck_staff_role_valid_period"),
            models.UniqueConstraint(
                fields=["staff", "role"],
                condition=Q(valid_until__isnull=True, division__isnull=True, department__isnull=True),
                name="uq_staff_role_global",
            ),
            models.UniqueConstraint(
                fields=["staff", "role", "division"],
                condition=Q(valid_until__isnull=True, division__isnull=False, department__isnull=True),
                name="uq_staff_role_division",
            ),
            models.UniqueConstraint(
                fields=["staff", "role", "department"],
                condition=Q(valid_until__isnull=True, division__isnull=True, department__isnull=False),
                name="uq_staff_role_dept",
            ),
            models.UniqueConstraint(
                fields=["staff", "role", "division", "department"],
                condition=Q(valid_until__isnull=True, division__isnull=False, department__isnull=False),
                name="uq_staff_role_div_dept",
            ),
        ]


class StaffDepartment(UUIDModel):
    staff = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["staff", "department"], name="uq_staff_department")]


class StaffDivision(UUIDModel):
    staff = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    division = models.ForeignKey(Division, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["staff", "division"], name="uq_staff_division")]


def staff_has_division_access(staff_id, division_id):
    """Return whether staff is assigned to a division or holds a global admin role."""
    if not staff_id or not division_id:
        return False
    now = timezone.now()
    return StaffDivision.objects.filter(
        staff_id=staff_id, division_id=division_id
    ).exists() or StaffRole.objects.filter(
        staff_id=staff_id,
        role__code__in=["founder", "super_admin"],
        division__isnull=True,
        department__isnull=True,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()


class Customer(UUIDModel, TimeStampedModel):
    customer_code = models.CharField(max_length=40, unique=True)
    display_name = models.CharField(max_length=180)
    mobile = models.CharField(max_length=30, blank=True, db_index=True)
    whatsapp_mobile = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=180, blank=True)
    customer_type = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name


class Enquiry(UUIDModel, TimeStampedModel):
    class Source(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"
        PHONE = "phone", "Phone"
        DIRECT = "direct_visit", "Direct Visit"
        REFERRAL = "referral", "Referral"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUOTATION_SENT = "quotation_sent", "Quotation Sent"
        FOLLOW_UP = "follow_up", "Follow-up"
        CONFIRMED = "confirmed", "Confirmed"
        LOST = "lost", "Lost"

    enquiry_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="enquiries")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="enquiries")
    enquiry_date = models.DateField(default=timezone.localdate)
    source = models.CharField(max_length=30, choices=Source.choices)
    requested_product_service = models.TextField()
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True)
    follow_up_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="created_enquiries")

    class Meta:
        indexes = [
            models.Index(fields=["division", "status", "enquiry_date"], name="ix_enquiry_div_status_date"),
            models.Index(fields=["assigned_to", "follow_up_at"], name="ix_enquiry_owner_followup"),
        ]

    def clean(self):
        errors = {}
        if self.assigned_to_id and self.division_id and not StaffDivision.objects.filter(
            staff_id=self.assigned_to_id, division_id=self.division_id
        ).exists():
            errors["assigned_to"] = "Assignee must belong to the enquiry division."
        if self.created_by_id and self.division_id and not staff_has_division_access(
            self.created_by_id, self.division_id
        ):
            errors["created_by"] = "Creator must belong to the enquiry division or hold a global Founder/Super Admin role."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class FollowUp(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, related_name="follow_ups")
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True)
    due_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    note = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "due_at"], name="ix_followup_status_due")]

    def clean(self):
        if self.assigned_to_id and self.enquiry_id and not StaffDivision.objects.filter(
            staff_id=self.assigned_to_id, division_id=self.enquiry.division_id
        ).exists():
            raise ValidationError({
                "assigned_to": "Assignee must belong to the enquiry division."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CustomerCommunication(UUIDModel):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        INSTAGRAM = "instagram", "Instagram"
        FACEBOOK = "facebook", "Facebook"
        PHONE = "phone", "Phone"
        EMAIL = "email", "Email"
        IN_PERSON = "in_person", "In Person"
        OTHER = "other", "Other"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="communications")
    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    channel = models.CharField(max_length=30, choices=Channel.choices)
    direction = models.CharField(max_length=20, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    summary = models.TextField()
    external_reference = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)

    def clean(self):
        errors = {}
        if self.enquiry_id and self.division_id:
            enquiry = self.enquiry
            if enquiry.division_id != self.division_id:
                errors["enquiry"] = "Enquiry must belong to the communication division."
            if enquiry.customer_id != self.customer_id:
                errors["customer"] = "Customer must match the selected enquiry."
        if self.recorded_by_id and self.division_id and not staff_has_division_access(
            self.recorded_by_id, self.division_id
        ):
            errors["recorded_by"] = "Recorder must belong to the communication division or hold a global Founder/Super Admin role."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ApprovalRequest(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    approval_type = models.CharField(max_length=60)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="approval_requests_made")
    decided_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="approval_decisions")
    requested_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    requested_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["division", "status", "requested_at"], name="ix_approval_div_status")]

    def clean(self):
        errors = {}
        for field in ("requested_by", "decided_by"):
            staff_id = getattr(self, f"{field}_id")
            if staff_id and self.division_id and not staff_has_division_access(
                staff_id, self.division_id
            ):
                errors[field] = "Staff member must belong to the approval division or hold a global Founder/Super Admin role."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Quotation(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending_approval", "Pending Approval"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    quotation_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotations")
    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="INR")
    terms = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    prepared_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="prepared_quotations")
    approved_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_quotations")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(subtotal__gte=0) & Q(discount_amount__gte=0) & Q(total_amount__gte=0), name="ck_quotation_nonnegative"),
            models.CheckConstraint(condition=Q(valid_until__isnull=True) | Q(issue_date__isnull=True) | Q(valid_until__gte=models.F("issue_date")), name="ck_quotation_valid_dates"),
        ]
        indexes = [models.Index(fields=["division", "status", "issue_date"], name="ix_quote_div_status_date")]

    def clean(self):
        errors = {}
        if self.enquiry_id:
            enquiry = self.enquiry
            if enquiry.division_id != self.division_id:
                errors["enquiry"] = "Enquiry must belong to the quotation division."
            if enquiry.customer_id != self.customer_id:
                errors["customer"] = "Customer must match the selected enquiry."
        for field in ("prepared_by", "approved_by"):
            staff_id = getattr(self, f"{field}_id")
            if staff_id and self.division_id and not staff_has_division_access(staff_id, self.division_id):
                errors[field] = "Staff member must belong to the quotation division or hold a global Founder/Super Admin role."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class QuotationItem(UUIDModel):
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name="items")
    line_number = models.PositiveIntegerField()
    description = models.TextField()
    dimensions = models.JSONField(null=True, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=30)
    material_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    labour_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    machine_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    finishing_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    packing_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    delivery_installation_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["quotation", "line_number"], name="uq_quote_item_line"),
            models.CheckConstraint(condition=Q(quantity__gt=0) & Q(unit_price__gte=0) & Q(line_total__gte=0), name="ck_quote_item_values"),
        ]


class SalesOrder(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        ADVANCE_PENDING = "advance_pending", "Advance Pending"
        DESIGN = "design", "Design"
        CUSTOMER_APPROVAL = "customer_approval", "Customer Approval"
        MATERIAL_ALLOCATION = "material_allocation", "Material Allocation"
        PRODUCTION = "production", "Production"
        FINISHING = "finishing", "Finishing"
        QC = "qc", "QC"
        PACKING = "packing", "Packing"
        DELIVERY = "delivery", "Delivery"
        FINAL_PAYMENT = "final_payment", "Final Payment"
        CLOSED = "closed", "Closed"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    order_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="orders")
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CONFIRMED)
    order_date = models.DateField(default=timezone.localdate)
    delivery_due_date = models.DateField(null=True, blank=True)
    installation_required = models.BooleanField(default=False)
    installation_address = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    advance_required = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    advance_received = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    approved_credit = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="created_orders")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(subtotal__gte=0) & Q(discount_amount__gte=0) & Q(grand_total__gte=0) & Q(advance_received__gte=0) & Q(balance_due__gte=0), name="ck_order_nonnegative"),
            models.CheckConstraint(condition=Q(delivery_due_date__isnull=True) | Q(delivery_due_date__gte=models.F("order_date")), name="ck_order_delivery_date"),
        ]
        indexes = [
            models.Index(fields=["division", "status", "order_date"], name="ix_order_div_status_date"),
            models.Index(fields=["delivery_due_date"], name="ix_order_delivery_due"),
        ]

    def clean(self):
        errors = {}
        if self.quotation_id:
            quotation = self.quotation
            if quotation.division_id != self.division_id:
                errors["quotation"] = "Quotation must belong to the sales order division."
            if quotation.customer_id != self.customer_id:
                errors["customer"] = "Customer must match the selected quotation."
        if self.created_by_id and self.division_id and not staff_has_division_access(self.created_by_id, self.division_id):
            errors["created_by"] = "Order creator must belong to the sales order division or hold a global Founder/Super Admin role."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OrderItem(UUIDModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="items")
    line_number = models.PositiveIntegerField()
    description = models.TextField()
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=30)
    dimensions = models.JSONField(null=True, blank=True)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    requirements = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sales_order", "line_number"], name="uq_order_item_line"),
            models.CheckConstraint(condition=Q(quantity__gt=0) & Q(unit_price__gte=0) & Q(line_total__gte=0), name="ck_order_item_values"),
        ]


class OrderAssignment(UUIDModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="assignments")
    staff = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    assignment_type = models.CharField(max_length=40)
    assigned_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="order_assignments_made")
    assigned_at = models.DateTimeField(default=timezone.now)
    unassigned_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.sales_order_id:
            division_id = self.sales_order.division_id
            for field in ("staff", "assigned_by"):
                staff_id = getattr(self, f"{field}_id")
                if staff_id and not (staff_has_division_access(staff_id, division_id) if field == "assigned_by" else StaffDivision.objects.filter(staff_id=staff_id, division_id=division_id).exists()):
                    raise ValidationError({field: "Assigned staff must belong to the sales order division; assigner must belong or hold a global Founder/Super Admin role."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OrderStatusEvent(UUIDModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="status_events")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    changed_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(blank=True)

    def clean(self):
        if self.sales_order_id and self.changed_by_id and not staff_has_division_access(
            self.changed_by_id, self.sales_order.division_id
        ):
            raise ValidationError({
                "changed_by": "Status actor must belong to the sales order division or hold a global Founder/Super Admin role."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DesignRecord(UUIDModel, TimeStampedModel):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="design_records")
    title = models.CharField(max_length=180)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=40, default="pending")
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True)

    def clean(self):
        if self.assigned_to_id and self.sales_order_id and not StaffDivision.objects.filter(
            staff_id=self.assigned_to_id, division_id=self.sales_order.division_id
        ).exists():
            raise ValidationError({"assigned_to": "Designer must belong to the sales order division."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class StoredFile(UUIDModel):
    storage_key = models.TextField(unique=True)
    original_name = models.TextField()
    mime_type = models.CharField(max_length=150)
    byte_size = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    is_private = models.BooleanField(default=True)


class DesignRevisionQuerySet(models.QuerySet):
    def _assert_unlocked(self):
        if self.filter(locked_at__isnull=False).exists():
            raise ValidationError(
                "An approved design revision is immutable; create a new revision."
            )

    def update(self, **kwargs):
        self._assert_unlocked()
        if "locked_at" in kwargs or kwargs.get("status") == "approved":
            raise ValidationError(
                "Design revisions can only be approved through the approval workflow."
            )
        return super().update(**kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        revision_ids = [obj.pk for obj in objs if obj.pk is not None]
        if DesignRevision.objects.filter(
            pk__in=revision_ids, locked_at__isnull=False
        ).exists():
            raise ValidationError(
                "An approved design revision is immutable; create a new revision."
            )
        if {"locked_at", "status"}.intersection(fields):
            raise ValidationError(
                "Design revision approval fields must be changed through the approval workflow."
            )
        return super().bulk_update(objs, fields, batch_size=batch_size)

    def bulk_create(self, objs, **kwargs):
        objects = list(objs)
        if any(obj.locked_at is not None or obj.status == "approved" for obj in objects):
            raise ValidationError(
                "Create a design revision first, then approve it through the approval workflow."
            )
        return super().bulk_create(objects, **kwargs)

    def delete(self):
        self._assert_unlocked()
        return super().delete()


class DesignRevisionManager(models.Manager.from_queryset(DesignRevisionQuerySet)):
    pass


class DesignRevision(UUIDModel, TimeStampedModel):
    design_record = models.ForeignKey(DesignRecord, on_delete=models.PROTECT, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    status = models.CharField(max_length=40, default="pending")
    dimensions = models.JSONField(null=True, blank=True)
    change_summary = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    files = models.ManyToManyField(StoredFile, through="DesignRevisionFile", related_name="design_revisions")

    objects = DesignRevisionManager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["design_record", "revision_number"], name="uq_design_revision_number")]

    def save(self, *args, **kwargs):
        if self._state.adding and (self.locked_at is not None or self.status == "approved"):
            raise ValidationError(
                "A design revision must be created unlocked and approved through the workflow."
            )
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.locked_at:
                changed = [
                    field.name for field in self._meta.concrete_fields
                    if getattr(previous, field.attname) != getattr(self, field.attname)
                    and field.name != "updated_at"
                ]
                if changed:
                    raise ValidationError(
                        "An approved design revision is immutable; create a new revision. "
                        f"Changed fields: {', '.join(changed)}"
                    )
            if previous and previous.locked_at is None and (
                self.locked_at is not None or self.status == "approved"
            ):
                if not getattr(self, "_approval_workflow_update", False):
                    raise ValidationError(
                        "Design revisions can only be approved through the approval workflow."
                    )
                if not self.approvals.filter(
                    reviewer_type="customer", decision="approved"
                ).exists() or not self.approvals.filter(
                    reviewer_type="manager", decision="approved"
                ).exists():
                    raise ValidationError(
                        "Customer and Manager approvals are required before locking a revision."
                    )
        super().save(*args, **kwargs)

    def lock_after_approval(self, manager_approval):
        if (
            manager_approval.design_revision_id != self.pk
            or manager_approval.reviewer_type != "manager"
            or manager_approval.decision != "approved"
            or not self.approvals.filter(
                reviewer_type="customer", decision="approved"
            ).exists()
        ):
            raise ValidationError(
                "A valid Manager approval and prior customer approval are required."
            )
        self.status = "approved"
        self.locked_at = manager_approval.reviewed_at or timezone.now()
        self._approval_workflow_update = True
        try:
            self.save(update_fields=["status", "locked_at", "updated_at"])
        finally:
            del self._approval_workflow_update

    def delete(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(
            pk=self.pk, locked_at__isnull=False
        ).exists():
            raise ValidationError(
                "An approved design revision is immutable; create a new revision."
            )
        return super().delete(*args, **kwargs)


class DesignRevisionFileQuerySet(models.QuerySet):
    def _assert_revisions_unlocked(self, revision_ids=None):
        locked = DesignRevision.objects.filter(locked_at__isnull=False)
        if revision_ids is not None:
            locked = locked.filter(pk__in=revision_ids)
        if self.filter(design_revision__in=locked).exists():
            raise ValidationError(
                "Files attached to an approved design revision are immutable."
            )

    def delete(self):
        self._assert_revisions_unlocked()
        return super().delete()

    def update(self, **kwargs):
        self._assert_revisions_unlocked()
        if "design_revision" in kwargs or "design_revision_id" in kwargs:
            target_id = kwargs.get("design_revision_id", kwargs.get("design_revision"))
            if target_id is not None and DesignRevision.objects.filter(
                pk=target_id, locked_at__isnull=False
            ).exists():
                raise ValidationError(
                    "Files cannot be attached to an approved design revision."
                )
        return super().update(**kwargs)

    def bulk_create(self, objs, **kwargs):
        objects = list(objs)
        revision_ids = {
            obj.design_revision_id for obj in objects
            if getattr(obj, "design_revision_id", None) is not None
        }
        if DesignRevision.objects.filter(
            pk__in=revision_ids, locked_at__isnull=False
        ).exists():
            raise ValidationError(
                "Files cannot be attached to an approved design revision."
            )
        return super().bulk_create(objects, **kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        objects = list(objs)
        attachment_ids = [obj.pk for obj in objects if obj.pk is not None]
        locked_revisions = DesignRevision.objects.filter(locked_at__isnull=False)
        if self.filter(
            pk__in=attachment_ids, design_revision__in=locked_revisions
        ).exists():
            raise ValidationError(
                "Files attached to an approved design revision are immutable."
            )
        if "design_revision" in fields:
            target_revision_ids = {
                obj.design_revision_id for obj in objects
                if obj.design_revision_id is not None
            }
            if locked_revisions.filter(pk__in=target_revision_ids).exists():
                raise ValidationError(
                    "Files cannot be attached to an approved design revision."
                )
        return super().bulk_update(objects, fields, batch_size=batch_size)


class DesignRevisionFileManager(models.Manager.from_queryset(DesignRevisionFileQuerySet)):
    pass


class DesignRevisionFile(UUIDModel):
    design_revision = models.ForeignKey(DesignRevision, on_delete=models.PROTECT)
    stored_file = models.ForeignKey(StoredFile, on_delete=models.PROTECT)

    objects = DesignRevisionFileManager()

    class Meta:
        base_manager_name = "objects"
        default_manager_name = "objects"
        constraints = [models.UniqueConstraint(fields=["design_revision", "stored_file"], name="uq_design_revision_file")]

    def _assert_revision_unlocked(self):
        if self.design_revision_id and DesignRevision.objects.filter(
            pk=self.design_revision_id, locked_at__isnull=False
        ).exists():
            raise ValidationError(
                "Files attached to an approved design revision are immutable."
            )

    def save(self, *args, **kwargs):
        self._assert_revision_unlocked()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._assert_revision_unlocked()
        return super().delete(*args, **kwargs)


def protect_locked_revision_file_attachments(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in {"pre_add", "pre_remove", "pre_clear"}:
        return

    if reverse:
        revision_ids = set(pk_set or [])
        if action == "pre_clear":
            revision_ids = set(
                sender.objects.filter(stored_file=instance).values_list(
                    "design_revision_id", flat=True
                )
            )
    else:
        revision_ids = {instance.pk}

    if revision_ids and DesignRevision.objects.filter(
        pk__in=revision_ids, locked_at__isnull=False
    ).exists():
        raise ValidationError(
            "Files attached to an approved design revision are immutable."
        )


class DesignApprovalQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Design approval history is immutable.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Design approval history is immutable.")

    def delete(self):
        raise ValidationError("Design approval history cannot be deleted.")


class DesignApprovalManager(models.Manager.from_queryset(DesignApprovalQuerySet)):
    pass


class DesignApproval(UUIDModel):
    design_revision = models.ForeignKey(DesignRevision, on_delete=models.PROTECT, related_name="approvals")
    reviewer_type = models.CharField(max_length=30)
    decision = models.CharField(max_length=24)
    reviewed_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)

    objects = DesignApprovalManager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Design approval history is immutable; record a new decision.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Design approval history cannot be deleted.")


class JobCardQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError(
            "Job cards must be saved through model validation; queryset updates are disabled."
        )

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError(
            "Job cards must be saved through model validation; bulk updates are disabled."
        )

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False, update_conflicts=False,
                    update_fields=None, unique_fields=None):
        objects = list(objs)
        for job_card in objects:
            job_card.full_clean()
        return super().bulk_create(
            objects,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


class JobCardManager(models.Manager.from_queryset(JobCardQuerySet)):
    pass


class JobCard(UUIDModel, TimeStampedModel):
    job_number = models.CharField(max_length=40, unique=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name="job_cards")
    approved_design_revision = models.ForeignKey(DesignRevision, on_delete=models.PROTECT)
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, default="pending")
    planned_start = models.DateField(null=True, blank=True)
    planned_completion = models.DateField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_completion = models.DateTimeField(null=True, blank=True)
    requirements = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    objects = JobCardManager()

    def clean(self):
        if not self.approved_design_revision_id or not self.sales_order_id or not self.division_id:
            raise ValidationError("A job card requires a sales order, division, and approved design revision.")
        if self.approved_design_revision_id and self.sales_order_id:
            revision = self.approved_design_revision
            if revision.design_record.sales_order_id != self.sales_order_id:
                raise ValidationError("Design revision must belong to the same order as the job card.")
            if revision.status != "approved" or not revision.locked_at:
                raise ValidationError("A job card requires a locked, approved design revision.")
            if revision.design_record.sales_order.division_id != self.division_id:
                raise ValidationError("Job card division must match the sales order division.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductionStage(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        REWORK = "rework_required", "Rework Required"

    job_card = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name="stages")
    stage_code = models.SlugField(max_length=50)
    stage_name = models.CharField(max_length=120)
    sequence_number = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    planned_start = models.DateTimeField(null=True, blank=True)
    expected_completion = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_completion = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job_card", "sequence_number"], name="uq_stage_sequence")]

    def clean(self):
        if self.assigned_to_id and self.job_card_id and not StaffDivision.objects.filter(
            staff_id=self.assigned_to_id, division_id=self.job_card.division_id
        ).exists():
            raise ValidationError({"assigned_to": "Production assignee must belong to the job card division."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductionUpdate(UUIDModel):
    production_stage = models.ForeignKey(ProductionStage, on_delete=models.PROTECT, related_name="updates")
    staff = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    status = models.CharField(max_length=24)
    note = models.TextField(blank=True)
    evidence_file = models.ForeignKey(StoredFile, on_delete=models.PROTECT, null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        if self.staff_id and self.production_stage_id:
            division_id = self.production_stage.job_card.division_id
            if not StaffDivision.objects.filter(
                staff_id=self.staff_id, division_id=division_id
            ).exists():
                raise ValidationError({"staff": "Reporting staff member must belong to the job card division."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class StaffTask(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        REWORK = "rework_required", "Rework Required"

    task_number = models.CharField(max_length=40, unique=True)
    division = models.ForeignKey(Division, on_delete=models.PROTECT)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, null=True, blank=True)
    job_card = models.ForeignKey(JobCard, on_delete=models.PROTECT, null=True, blank=True)
    production_stage = models.ForeignKey(ProductionStage, on_delete=models.PROTECT, null=True, blank=True)
    assigned_to = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="assigned_tasks")
    assigned_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, related_name="tasks_created")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20)
    assigned_at = models.DateTimeField(default=timezone.now)
    deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ASSIGNED)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["assigned_to", "status", "deadline"], name="ix_task_owner_status_due")]

    def clean(self):
        related_order_id = None
        if self.sales_order_id:
            related_order_id = self.sales_order_id
            if self.sales_order.division_id != self.division_id:
                raise ValidationError({"sales_order": "Sales order must belong to the task division."})
        if self.job_card_id:
            if self.job_card.division_id != self.division_id:
                raise ValidationError({"job_card": "Job card must belong to the task division."})
            if related_order_id and self.job_card.sales_order_id != related_order_id:
                raise ValidationError({"job_card": "Job card must belong to the selected sales order."})
            related_order_id = self.job_card.sales_order_id
        if self.production_stage_id:
            stage = self.production_stage
            if not self.job_card_id or stage.job_card_id != self.job_card_id:
                raise ValidationError({"production_stage": "Production stage must belong to the selected job card."})
            if stage.job_card.division_id != self.division_id:
                raise ValidationError({"production_stage": "Production stage must belong to the task division."})
        for field in ("assigned_to", "assigned_by"):
            staff_id = getattr(self, f"{field}_id")
            if staff_id and not (staff_has_division_access(staff_id, self.division_id) if field == "assigned_by" else StaffDivision.objects.filter(staff_id=staff_id, division_id=self.division_id).exists()):
                raise ValidationError({field: "Assigned staff must belong to the task division; assigner must belong or hold a global Founder/Super Admin role."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TaskUpdate(UUIDModel):
    class UpdateType(models.TextChoices):
        PROGRESS = "progress", "Progress"
        COMPLETION = "completion", "Completion"
        DELAY = "delay", "Delay"
        ISSUE = "issue", "Issue"
        MATERIAL_NEED = "material_need", "Material Need"

    staff_task = models.ForeignKey(StaffTask, on_delete=models.PROTECT, related_name="updates")
    reported_by = models.ForeignKey(StaffProfile, on_delete=models.PROTECT)
    update_type = models.CharField(max_length=30, choices=UpdateType.choices)
    note = models.TextField(blank=True)
    evidence_file = models.ForeignKey(StoredFile, on_delete=models.PROTECT, null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        if self.staff_task_id and self.reported_by_id and not StaffDivision.objects.filter(
            staff_id=self.reported_by_id, division_id=self.staff_task.division_id
        ).exists():
            raise ValidationError({
                "reported_by": "Task update reporter must belong to the staff task division."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AuditEvent(UUIDModel):
    actor = models.ForeignKey(StaffProfile, on_delete=models.PROTECT, null=True, blank=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=40)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    request_id = models.CharField(max_length=100, blank=True)

    class Meta:
        indexes = [models.Index(fields=["entity_type", "entity_id", "occurred_at"], name="ix_audit_entity_time")]
        ordering = ["-occurred_at"]
