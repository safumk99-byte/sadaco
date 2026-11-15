from datetime import date
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ProductCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children",
    )
    is_section = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["parent__name", "name"]
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=180)
    sku = models.CharField(max_length=60, unique=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
    )
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=40, default="Piece")
    # Legacy customer-price column retained for compatibility with older reports.
    # Internal products do not use customer selling price; the value defaults to 0.
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    # Existing selling_price is retained for backward compatibility.
    actual_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    discount_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    customer_visible = models.BooleanField(default=False)
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        blank=True,
        null=True,
    )
    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    stock_quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def discount_percentage(self):
        if self.actual_price and self.discount_price and self.discount_price < self.actual_price:
            return round((self.actual_price - self.discount_price) * 100 / self.actual_price)
        return 0

    @property
    def customer_price(self):
        if self.discount_price and self.discount_price < self.actual_price:
            return self.discount_price
        return self.actual_price or self.selling_price

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        IN = "in", "Stock In"
        OUT = "out", "Stock Out"
        ADJUSTMENT = "adjustment", "Adjustment"

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="stock_transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    balance_after = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    reference = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stock_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["transaction_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.product.sku} - {self.get_transaction_type_display()} - {self.quantity}"



class MaterialVariant(models.Model):
    """Purchasable material master; purchase and retail rates are independent."""
    class Colour(models.TextChoices):
        CLEAR = "clear", "Clear"
        COLOUR = "colour", "Colour"
        NOT_APPLICABLE = "na", "Not applicable"

    material_name = models.CharField(max_length=120)
    brand = models.CharField(max_length=120, blank=True)
    thickness_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    variant = models.CharField(max_length=120, blank=True)
    colour = models.CharField(max_length=12, choices=Colour.choices, default=Colour.NOT_APPLICABLE)
    sheet_width_ft = models.DecimalField(max_digits=7, decimal_places=2, default=8)
    sheet_height_ft = models.DecimalField(max_digits=7, decimal_places=2, default=4)
    purchase_rate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    retail_rate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    supplier_name = models.CharField(max_length=180, blank=True)
    stock_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit = models.CharField(max_length=30, default="Sheet")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["material_name", "brand", "thickness_mm", "variant", "colour"]
        constraints = [
            models.UniqueConstraint(
                fields=["material_name", "brand", "thickness_mm", "variant", "colour"],
                name="products_material_variant_unique",
            )
        ]

    @property
    def sheet_area_sqft(self):
        return self.sheet_width_ft * self.sheet_height_ft

    def save(self, *args, **kwargs):
        previous_rates = None
        if self.pk:
            previous_rates = type(self).objects.filter(pk=self.pk).values(
                "purchase_rate", "retail_rate"
            ).first()
        super().save(*args, **kwargs)
        current_rates = (self.purchase_rate, self.retail_rate)
        old_rates = (
            (previous_rates["purchase_rate"], previous_rates["retail_rate"])
            if previous_rates else None
        )
        if old_rates != current_rates:
            MaterialRateHistory.objects.create(
                material=self,
                purchase_rate=self.purchase_rate,
                retail_rate=self.retail_rate,
                effective_from=date.today(),
                changed_by=getattr(self, "_rate_changed_by", None),
                note="Initial rate record" if old_rates is None else "Rate updated",
            )

    @property
    def purchase_rate_sqft(self):
        if self.purchase_rate is None or not self.sheet_area_sqft:
            return None
        return self.purchase_rate / self.sheet_area_sqft

    @property
    def retail_rate_sqft(self):
        if self.retail_rate is None or not self.sheet_area_sqft:
            return None
        return self.retail_rate / self.sheet_area_sqft

    def __str__(self):
        parts = [self.material_name, self.brand, f"{self.thickness_mm}mm" if self.thickness_mm else "", self.variant, self.get_colour_display()]
        return " - ".join(str(part) for part in parts if part)


class MaterialRateHistory(models.Model):
    material = models.ForeignKey(MaterialVariant, on_delete=models.CASCADE, related_name="rate_history")
    purchase_rate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    retail_rate = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    effective_from = models.DateField()
    changed_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from", "-created_at"]


class MachineRate(models.Model):
    class Operation(models.TextChoices):
        LASER_CUTTING = "laser_cutting", "Laser Cutting"
        LASER_ENGRAVING = "laser_engraving", "Laser Engraving"
        CNC_CUTTING = "cnc_cutting", "CNC Cutting"

    operation = models.CharField(max_length=30, choices=Operation.choices)
    material_name = models.CharField(max_length=120, blank=True)
    thickness_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=20, default="minute")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["operation", "material_name", "thickness_mm"]


class StaffCompensation(models.Model):
    class PaymentType(models.TextChoices):
        MONTHLY = "monthly", "Monthly Salary"
        PER_WORK = "per_work", "Work-based Payment"

    staff = models.OneToOneField("staff.StaffProfile", on_delete=models.CASCADE, related_name="compensation")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    working_days_per_month = models.PositiveSmallIntegerField(default=26)
    productive_hours_per_day = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("8.25"))
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def monthly_productive_hours(self):
        return Decimal(self.working_days_per_month) * self.productive_hours_per_day

    @property
    def hourly_cost(self):
        if self.payment_type != self.PaymentType.MONTHLY or self.monthly_salary is None:
            return None
        hours = self.monthly_productive_hours
        if hours <= 0:
            return None
        return self.monthly_salary / hours
