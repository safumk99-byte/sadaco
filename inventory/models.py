from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class MaterialIssue(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        CANCELLED = "cancelled", "Cancelled"

    job = models.ForeignKey(
        "production.ProductionJob",
        on_delete=models.PROTECT,
        related_name="material_issues",
    )
    material = models.ForeignKey(
        "production.ProductionMaterial",
        on_delete=models.PROTECT,
        related_name="inventory_issues",
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ISSUED)
    reference = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_issues",
    )
    issued_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["material", "status"]),
        ]

    def __str__(self):
        return f"{self.job.job_no} - {self.material.material_name} - {self.quantity}"


class StockCount(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="stock_counts",
    )
    system_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    counted_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    variance = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_counts",
    )
    counted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-counted_at"]
        indexes = [models.Index(fields=["product", "-counted_at"])]

    def __str__(self):
        return f"{self.product.sku} count {self.counted_quantity}"


class ReorderAlert(models.Model):
    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory_reorder_alert",
    )
    is_open = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reorder: {self.product.sku}"
