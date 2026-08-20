from django.core.validators import MinValueValidator
from django.db import models


class ProductCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
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
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
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
