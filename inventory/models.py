from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class MaterialIssue(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        CANCELLED = "cancelled", "Cancelled"

    job = models.ForeignKey("production.ProductionJob", on_delete=models.PROTECT, related_name="material_issues")
    material = models.ForeignKey("production.ProductionMaterial", on_delete=models.PROTECT, related_name="inventory_issues")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    reference = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)
    stock_lot = models.ForeignKey("purchase.MaterialStockLot", on_delete=models.PROTECT, null=True, blank=True, related_name="issues")
    unit_rate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    stock_movement = models.OneToOneField("inventory.MaterialStockMovement", on_delete=models.PROTECT, null=True, blank=True, related_name="material_issue")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="material_issues")
    issued_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [models.Index(fields=["job", "status"]), models.Index(fields=["material", "status"])]

    def __str__(self):
        return f"{self.job.job_no} - {self.material.material_name} - {self.quantity}"


class StockCount(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"

    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="stock_counts")
    system_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    counted_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    variance = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_counts")
    counted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-counted_at"]
        indexes = [models.Index(fields=["product", "-counted_at"])]

    def __str__(self):
        return f"{self.product.sku} count {self.counted_quantity}"


class ReorderAlert(models.Model):
    product = models.OneToOneField("products.Product", on_delete=models.CASCADE, related_name="inventory_reorder_alert")
    is_open = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reorder: {self.product.sku}"


class MaterialStockBalance(models.Model):
    """Department/location balance for a shared MaterialVariant master."""
    material = models.ForeignKey("products.MaterialVariant", on_delete=models.PROTECT, related_name="stock_balances")
    department = models.ForeignKey("core.Department", on_delete=models.PROTECT, related_name="material_stock_balances")
    location = models.CharField(max_length=160)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    minimum_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department__name", "location", "material__material_name"]
        constraints = [models.UniqueConstraint(fields=["material", "department", "location"], name="inv_material_dept_location_uniq")]
        indexes = [models.Index(fields=["department", "location"])]

    def __str__(self):
        return f"{self.material} · {self.department} · {self.location}"


class MaterialStockMovement(models.Model):
    class Type(models.TextChoices):
        OPENING = "opening", "Opening"
        PURCHASE_RECEIPT = "purchase_receipt", "Purchase Receipt"
        JOB_ISSUE = "job_issue", "Job Issue"
        RETURN = "return", "Return"
        OFFCUT_IN = "offcut_in", "Reusable Offcut"
        WASTAGE = "wastage", "Wastage"
        CLOSING = "closing", "Closing"
        CORRECTION = "correction", "Authorized Correction"

    balance = models.ForeignKey(MaterialStockBalance, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=24, choices=Type.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0.001)])
    balance_after = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    job = models.ForeignKey("production.ProductionJob", on_delete=models.PROTECT, null=True, blank=True, related_name="material_stock_movements")
    order = models.ForeignKey("sales.SalesOrder", on_delete=models.PROTECT, null=True, blank=True, related_name="material_stock_movements")
    employee = models.ForeignKey("staff.StaffProfile", on_delete=models.PROTECT, null=True, blank=True, related_name="material_stock_movements")
    reference = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="material_stock_movements")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["balance", "-created_at"]), models.Index(fields=["movement_type", "-created_at"])]

    def __str__(self):
        return f"{self.balance.material} · {self.get_movement_type_display()} · {self.quantity}"


class ReusableOffcut(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        USED = "used", "Used"
        DISCARDED = "discarded", "Discarded"

    material = models.ForeignKey("products.MaterialVariant", on_delete=models.PROTECT, related_name="reusable_offcuts")
    department = models.ForeignKey("core.Department", on_delete=models.PROTECT, related_name="reusable_offcuts")
    location = models.CharField(max_length=160)
    thickness_mm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    length_mm = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    width_mm = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    usable_area_sqft = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(0.0001)])
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE)
    source_job = models.ForeignKey("production.ProductionJob", on_delete=models.PROTECT, null=True, blank=True, related_name="generated_offcuts")
    used_for_job = models.ForeignKey("production.ProductionJob", on_delete=models.PROTECT, null=True, blank=True, related_name="used_offcuts")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["department", "status"])]

    def __str__(self):
        return f"{self.material} · {self.length_mm}×{self.width_mm} mm"


class MaterialStockCount(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    balance = models.ForeignKey(MaterialStockBalance, on_delete=models.PROTECT, related_name="physical_counts")
    system_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    counted_quantity = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    variance = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="material_counts_submitted")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="material_counts_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    correction_movement = models.OneToOneField("inventory.MaterialStockMovement", on_delete=models.PROTECT, null=True, blank=True, related_name="physical_count")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"Count #{self.pk} · {self.balance} · variance {self.variance}"
