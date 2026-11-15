from django.contrib import admin

from .models import Product, ProductCategory, StockTransaction, MaterialVariant, MaterialRateHistory, MachineRate, StaffCompensation


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "cost_price", "stock_quantity", "status")
    list_filter = ("status", "category")
    search_fields = ("name", "sku")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("product", "transaction_type", "quantity", "balance_after", "reference", "created_by", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("product__name", "product__sku", "reference")
    readonly_fields = ("created_at", "balance_after")


@admin.register(MaterialVariant)
class MaterialVariantAdmin(admin.ModelAdmin):
    list_display = ("material_name", "brand", "thickness_mm", "variant", "colour", "purchase_rate", "retail_rate", "is_active")
    list_filter = ("material_name", "brand", "colour", "is_active")
    search_fields = ("material_name", "brand", "variant", "supplier_name")

    def save_model(self, request, obj, form, change):
        obj._rate_changed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MaterialRateHistory)
class MaterialRateHistoryAdmin(admin.ModelAdmin):
    list_display = ("material", "purchase_rate", "retail_rate", "effective_from", "changed_by")
    readonly_fields = ("created_at",)


@admin.register(MachineRate)
class MachineRateAdmin(admin.ModelAdmin):
    list_display = ("operation", "material_name", "thickness_mm", "rate", "unit", "is_active")
    list_filter = ("operation", "is_active")


@admin.register(StaffCompensation)
class StaffCompensationAdmin(admin.ModelAdmin):
    list_display = ("staff", "payment_type", "monthly_salary", "is_active")
    list_filter = ("payment_type", "is_active")
