from django.db import migrations


def remove_demo_catalog_data(apps, schema_editor):
    # Only the demo product catalogue and its stock ledger are cleared.
    # Customers, order requests, orders, quotations, finance, staff activity,
    # users, staff profiles and departments are intentionally preserved.
    StockTransaction = apps.get_model("products", "StockTransaction")
    Product = apps.get_model("products", "Product")
    Category = apps.get_model("products", "ProductCategory")

    StockTransaction.objects.all().delete()

    # Existing order requests are retained. Keep any product that is referenced
    # by a request rather than breaking that request's product relation.
    Product.objects.exclude(customer_order_requests__isnull=False).delete()

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
    ]

    operations = [
        migrations.RunPython(remove_demo_catalog_data, migrations.RunPython.noop),
    ]
