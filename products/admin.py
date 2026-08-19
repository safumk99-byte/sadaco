from django.contrib import admin

from .models import Product, ProductCategory, StockTransaction


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "selling_price", "stock_quantity", "status")
    list_filter = ("status", "category")
    search_fields = ("name", "sku")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("product", "transaction_type", "quantity", "balance_after", "reference", "created_by", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("product__name", "product__sku", "reference")
    readonly_fields = ("created_at", "balance_after")
