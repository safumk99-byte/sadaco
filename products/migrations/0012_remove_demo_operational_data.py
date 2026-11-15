from django.db import migrations


def remove_demo_catalog_data(apps, schema_editor):
    # Only unreferenced demo catalogue rows are cleared; stock-ledger entries are guarded.
    # Customers, order requests, orders, quotations, finance, staff activity,
    # users, staff profiles and departments are intentionally preserved.
    StockTransaction = apps.get_model("products", "StockTransaction")
    Product = apps.get_model("products", "Product")
    Category = apps.get_model("products", "ProductCategory")

    # Existing order requests are retained. Keep any product that is referenced
    # by a request rather than breaking that request's product relation.
    # Preserve purchasing and production-linked rows. Inventory relations are
    # introduced after this migration in the dependency graph; their PROTECT
    # foreign keys still prevent deletion if a physical count references a row.
    demo_products = (
        Product.objects
        .exclude(customer_order_requests__isnull=False)
        .exclude(purchase_items__isnull=False)
        .exclude(production_materials__isnull=False)
        # A non-zero balance is operational stock even when the legacy ledger
        # has no transaction rows. Never discard it as catalogue demo data.
        .exclude(stock_quantity__gt=0)
    )
    if StockTransaction.objects.filter(product__in=demo_products).exists():
        raise RuntimeError(
            "Demo catalogue cleanup stopped: product stock transactions exist and require review."
        )
    demo_products.delete()

    # Remove empty demo categories from leaves upward; preserve any category
    # still used by a retained product.
    while Category.objects.exists():
        used_category_ids = Product.objects.values_list("category_id", flat=True)
        leaf_ids = list(
            Category.objects.exclude(pk__in=used_category_ids).exclude(
                pk__in=Category.objects.exclude(parent__isnull=True).values_list("parent_id", flat=True)
            ).values_list("pk", flat=True)
        )
        if not leaf_ids:
            break
        Category.objects.filter(pk__in=leaf_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0011_seed_staff_compensation"),
        ("sales", "0007_customer_department"),
        # The cleanup queries the historical reverse ProductionMaterial relation.
        # Ensure that relation exists in migration state before running it.
        ("production", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_demo_catalog_data, migrations.RunPython.noop),
    ]
