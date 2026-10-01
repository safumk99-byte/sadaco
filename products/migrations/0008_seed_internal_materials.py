from decimal import Decimal
from django.db import migrations


INTERNAL_CATEGORIES = [
    "Acrylic",
    "Sticker",
    "Other Materials",
]

# Rates transcribed from the supplier sheets/invoice supplied for this update.
# Initial stock is deliberately zero: these are master records, not demo stock.
PRODUCTS = [
    # Indian acrylic sheet
    ("2MM Indian Acrylic", "ACR-2IN", "Acrylic", "Sheet", "495.00"),
    ("3MM Indian Acrylic", "ACR-3IN", "Acrylic", "Sheet", "595.00"),
    ("4MM Indian Acrylic", "ACR-4IN", "Acrylic", "Sheet", "860.00"),
    ("5MM Indian Acrylic", "ACR-5IN", "Acrylic", "Sheet", "1105.00"),
    ("6MM Indian Acrylic", "ACR-6IN", "Acrylic", "Sheet", "1290.00"),

    # Astari acrylic, colour 8x4 sheet rates
    ("Astari Acrylic 2.5MM - Colour 8x4", "ACR-AST-25-C", "Acrylic", "Sheet", "3802.00"),
    ("Astari Acrylic 2.7/2.8MM - Colour 8x4", "ACR-AST-28-C", "Acrylic", "Sheet", "3922.00"),
    ("Astari Acrylic 3/3.5MM - Colour 8x4", "ACR-AST-35-C", "Acrylic", "Sheet", "5069.00"),
    ("Astari Acrylic 3.7/3.8MM - Colour 8x4", "ACR-AST-38-C", "Acrylic", "Sheet", "5297.00"),
    ("Astari Acrylic 4/4.5MM - Colour 8x4", "ACR-AST-45-C", "Acrylic", "Sheet", "6336.00"),
    ("Astari Acrylic 4.7/4.8MM - Colour 8x4", "ACR-AST-48-C", "Acrylic", "Sheet", "6870.00"),
    ("Astari Acrylic 5.7/5.8MM - Colour 8x4", "ACR-AST-58-C", "Acrylic", "Sheet", "8302.00"),
    ("Astari Acrylic 7.7/7.8MM - Colour 8x4", "ACR-AST-78-C", "Acrylic", "Sheet", "11165.00"),

    # Astari acrylic, clear 8x4 sheet rates
    ("Astari Acrylic 1.8MM - Clear 8x4", "ACR-AST-18-CL", "Acrylic", "Sheet", "2760.00"),
    ("Astari Acrylic 2.5MM - Clear 8x4", "ACR-AST-25-CL", "Acrylic", "Sheet", "3716.00"),
    ("Astari Acrylic 2.7/2.8MM - Clear 8x4", "ACR-AST-28-CL", "Acrylic", "Sheet", "3744.00"),
    ("Astari Acrylic 3/3.5MM - Clear 8x4", "ACR-AST-35-CL", "Acrylic", "Sheet", "4954.00"),
    ("Astari Acrylic 3.7/3.8MM - Clear 8x4", "ACR-AST-38-CL", "Acrylic", "Sheet", "4997.00"),
    ("Astari Acrylic 4/4.5MM - Clear 8x4", "ACR-AST-45-CL", "Acrylic", "Sheet", "6192.00"),
    ("Astari Acrylic 4.7/4.8MM - Clear 8x4", "ACR-AST-48-CL", "Acrylic", "Sheet", "6482.00"),
    ("Astari Acrylic 5.7/5.8MM - Clear 8x4", "ACR-AST-58-CL", "Acrylic", "Sheet", "7832.00"),
    ("Astari Acrylic 7.7/7.8MM - Clear 8x4", "ACR-AST-78-CL", "Acrylic", "Sheet", "10532.00"),

    # Gum sheet invoice rates (rate excluding tax, per Nos)
    ("Gum Sheet 12x18 PET White (PVC) 8544", "STK-GUM-8544", "Sticker", "Nos", "14.195"),
    ("Gum Sheet 12x18 Clear 8543", "STK-GUM-8543", "Sticker", "Nos", "14.195"),
]


def seed_internal_materials(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")
    Product = apps.get_model("products", "Product")

    categories = {}
    for name in INTERNAL_CATEGORIES:
        category, _ = ProductCategory.objects.get_or_create(
            name=name,
            defaults={
                "parent": None,
                "is_section": False,
                "description": "Internal inventory/material category.",
                "is_active": True,
            },
        )
        categories[name] = category

    for name, sku, category_name, unit, cost in PRODUCTS:
        Product.objects.get_or_create(
            sku=sku,
            defaults={
                "name": name,
                "category": categories[category_name],
                "description": "Supplier rate provided for SADACO internal material management.",
                "unit": unit,
                "selling_price": Decimal("0"),
                "actual_price": Decimal("0"),
                "discount_price": Decimal("0"),
                "customer_visible": False,
                "cost_price": Decimal(cost),
                "stock_quantity": Decimal("0"),
                "low_stock_threshold": Decimal("0"),
                "status": "active",
            },
        )


def preserve_data_on_rollback(apps, schema_editor):
    # Do not delete seeded records on rollback; a user may have already
    # adjusted stock, price, or other details after migration.
    pass


class Migration(migrations.Migration):
    dependencies = [("products", "0007_internal_product_pricing_default")]

    operations = [
        migrations.RunPython(seed_internal_materials, preserve_data_on_rollback),
    ]
