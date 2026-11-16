from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
import uuid


class ProductionJob(models.Model):
    class Station(models.TextChoices):
        LASER = "laser", "Acrylic Laser Cutting"
        CNC = "cnc", "Wood CNC Cutting"
        MEMENTO = "memento", "Memento / Trophy"
        WALL_DECOR = "wall_decor", "Wall Décor"
        WOOD_CRAFT = "wood_craft", "Wood Craft & Polishing"
        RESIN = "resin", "Resin Products"
        CUSTOM = "custom", "Customized Products"

    class Stage(models.TextChoices):
        PLANNING = "planning", "Planning"
        MATERIAL_ALLOCATION = "material", "Material Allocation"
        DESIGN_CHECK = "design_check", "Design Check"
        PRODUCTION = "production", "Production"
        FINISHING = "finishing", "Finishing"
        QC_PENDING = "qc_pending", "Quality Check Pending"
        COMPLETED = "completed", "Completed"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    job_no = models.CharField(max_length=30, unique=True, editable=False)
    order = models.ForeignKey("sales.SalesOrder", on_delete=models.PROTECT, related_name="production_jobs")
    station = models.CharField(max_length=30, choices=Station.choices)
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.PLANNING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    assigned_staff = models.ForeignKey("staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="production_jobs")
    priority = models.CharField(max_length=20, choices=[("normal","Normal"),("high","High"),("urgent","Urgent")], default="normal")
    deadline = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0)])
    safety_checked = models.BooleanField(default=False)
    design_checked = models.BooleanField(default=False)
    material_ready = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_production_jobs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "deadline", "-created_at"]
        indexes = [models.Index(fields=["status", "deadline"]), models.Index(fields=["station", "status"]), models.Index(fields=["assigned_staff", "status"])]

    def save(self, *args, **kwargs):
        if not self.job_no:
            self.job_no = f"JOB-{uuid.uuid4().hex[:10].upper()}"
        if self.status == self.Status.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        if self.status == self.Status.COMPLETED:
            self.progress_percent = 100
            if not self.completed_at:
                self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.job_no


class ProductionProgress(models.Model):
    job = models.ForeignKey(ProductionJob, on_delete=models.CASCADE, related_name="progress_updates")
    stage = models.CharField(max_length=30, choices=ProductionJob.Stage.choices)
    progress_percent = models.PositiveSmallIntegerField(validators=[MinValueValidator(0)])
    note = models.TextField(blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ProductionMaterial(models.Model):
    job = models.ForeignKey(ProductionJob, on_delete=models.CASCADE, related_name="materials")
    # Product remains nullable for legacy finished-goods workflows. Raw materials use MaterialVariant.
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, null=True, blank=True, related_name="production_materials")
    material_variant = models.ForeignKey(
        "products.MaterialVariant", on_delete=models.PROTECT, null=True, blank=True,
        related_name="production_requirements",
    )
    material_name = models.CharField(max_length=180)
    quantity_required = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=40, default="Piece")
    issued_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    returned_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    wastage_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    issue_unit_rate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def offcut_consumed_area_sqft(self):
        if not self.material_variant_id:
            return Decimal("0")
        from django.db.models import Sum
        return self.offcut_usages.aggregate(total=Sum("used_area_sqft"))["total"] or Decimal("0")

    @property
    def offcut_equivalent_quantity(self):
        # Area-based offcuts fulfil a sheet-based requirement only. Do not
        # convert sq ft into unrelated units such as Piece, metre or kg.
        if not self.material_variant_id or self.unit.strip().casefold() not in {"sheet", "sheets"}:
            return Decimal("0")
        sheet_area = self.material_variant.sheet_area_sqft
        if sheet_area is None or sheet_area <= 0:
            return Decimal("0")
        return self.offcut_consumed_area_sqft / sheet_area

    @property
    def effective_fulfilled_quantity(self):
        supplied_sheets = max(self.issued_quantity - self.returned_quantity, Decimal("0"))
        return supplied_sheets + self.offcut_equivalent_quantity

    @property
    def pending_quantity(self):
        return max(self.quantity_required - self.effective_fulfilled_quantity, Decimal("0"))

    @property
    def actual_consumption(self):
        return max(self.issued_quantity - self.returned_quantity, 0)


class ProductionIssue(models.Model):
    class Type(models.TextChoices):
        DELAY = "delay", "Delay"
        REWORK = "rework", "Rework"

    job = models.ForeignKey(ProductionJob, on_delete=models.CASCADE, related_name="issues")
    issue_type = models.CharField(max_length=20, choices=Type.choices)
    stage = models.CharField(max_length=30, choices=ProductionJob.Stage.choices)
    reason = models.TextField()
    corrective_action = models.TextField(blank=True)
    staff = models.ForeignKey("staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
