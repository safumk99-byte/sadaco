from django.db import migrations


def remove_white_elegance(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")
    section = ProductCategory.objects.filter(name="WHITE ELEGANCE", parent__isnull=True).first()
    if not section:
        return

    # Never delete products or categories that are still referenced by products.
    # If the section is unused, remove its unused child categories and the section.
    children = ProductCategory.objects.filter(parent=section)
    for child in children:
        if child.products.exists():
            child.is_active = False
            child.save(update_fields=["is_active"])
        else:
            child.delete()

    if section.products.exists():
        section.is_active = False
        section.save(update_fields=["is_active"])
    else:
        section.delete()


def restore_white_elegance(apps, schema_editor):
    # Intentionally do not recreate deleted catalogue records on rollback.
    # This keeps customer/product data safe and avoids duplicate categories.
    pass


class Migration(migrations.Migration):
    dependencies = [("products", "0005_catalog_hierarchy")]
    operations = [migrations.RunPython(remove_white_elegance, restore_white_elegance)]
