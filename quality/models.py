from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class QualityCheck(models.Model):
    class CheckType(models.TextChoices):
        STATION = "station", "Station QC"
        FINAL = "final", "Final QC"

    class Result(models.TextChoices):
        PENDING = "pending", "Pending"
        PASS = "pass", "Passed"
        FAIL = "fail", "Failed"
        REWORK = "rework", "Rework Required"

    job = models.ForeignKey(
        "production.ProductionJob",
        on_delete=models.PROTECT,
        related_name="quality_checks",
    )
    check_type = models.CharField(max_length=20, choices=CheckType.choices)
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.PENDING)
    inspector = models.ForeignKey(
        "staff.StaffProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_checks",
    )
    stage = models.CharField(max_length=30, blank=True)
    design_match = models.BooleanField(default=False)
    measurement_ok = models.BooleanField(default=False)
    finishing_ok = models.BooleanField(default=False)
    colour_ok = models.BooleanField(default=False)
    engraving_ok = models.BooleanField(default=False)
    defects = models.TextField(blank=True)
    rework_reason = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    rework_count = models.PositiveSmallIntegerField(default=0)
    remarks = models.TextField(blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_quality_checks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "result"]),
            models.Index(fields=["check_type", "result"]),
        ]

    def save(self, *args, **kwargs):
        if self.result != self.Result.PENDING and not self.checked_at:
            self.checked_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def passed(self):
        return self.result == self.Result.PASS

    def __str__(self):
        return f"{self.job.job_no} - {self.get_check_type_display()}"


class ReworkRecord(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    quality_check = models.ForeignKey(
        QualityCheck, on_delete=models.CASCADE, related_name="reworks"
    )
    job = models.ForeignKey(
        "production.ProductionJob", on_delete=models.PROTECT, related_name="rework_records"
    )
    reason = models.TextField()
    corrective_action = models.TextField(blank=True)
    assigned_staff = models.ForeignKey(
        "staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="quality_rework_assignments",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_rework_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at"]

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class PackingRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PACKED = "packed", "Packed"

    job = models.OneToOneField(
        "production.ProductionJob", on_delete=models.PROTECT, related_name="packing"
    )
    packing_material = models.CharField(max_length=180, blank=True)
    fragile_protection = models.BooleanField(default=False)
    customer_label = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    packed_by = models.ForeignKey(
        "staff.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="packing_records",
    )
    packed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.status == self.Status.PACKED and not self.packed_at:
            self.packed_at = timezone.now()
        super().save(*args, **kwargs)
