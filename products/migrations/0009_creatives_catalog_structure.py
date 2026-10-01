from django.db import migrations


def seed_creatives(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")

    # Keep the customer catalogue focused on CREATIVES only.
    # Existing Royal Look data is preserved; the section is simply made inactive.
    royal = ProductCategory.objects.filter(name__iexact="ROYAL LOOK", parent__isnull=True).first()
    if royal:
        royal.is_active = False
        royal.is_section = True
        royal.save(update_fields=["is_active", "is_section"])

    section, _ = ProductCategory.objects.get_or_create(
        name="CREATIVES",
        defaults={"is_active": True, "is_section": True, "parent": None, "description": ""},
    )
    section.parent = None
    section.is_section = True
    section.is_active = True
    section.description = ""
    section.save(update_fields=["parent", "is_section", "is_active", "description"])

    categories = ["Wall Decors", "Mementoes"]
    for name in categories:
        category, _ = ProductCategory.objects.get_or_create(
            name=name,
            defaults={"is_active": True, "is_section": False, "parent": section, "description": ""},
        )
        # Do not move a category that already contains products unexpectedly.
        if not category.products.exists() or category.parent_id == section.pk:
            category.parent = section
            category.is_section = False
            category.is_active = True
            category.description = ""
            category.save(update_fields=["parent", "is_section", "is_active", "description"])

    mementoes = ProductCategory.objects.filter(name="Mementoes", parent=section).first()
    if mementoes:
        for name in ("First Prize", "Second Prize", "Third Prize", "Wedding Mementoes", "Other Mementoes"):
            subcategory, _ = ProductCategory.objects.get_or_create(
                name=name,
                defaults={"is_active": True, "is_section": False, "parent": mementoes, "description": ""},
            )
            if not subcategory.products.exists() or subcategory.parent_id == mementoes.pk:
                subcategory.parent = mementoes
                subcategory.is_section = False
                subcategory.is_active = True
                subcategory.description = ""
                subcategory.save(update_fields=["parent", "is_section", "is_active", "description"])


def preserve_catalog(apps, schema_editor):
    # Intentionally do not delete seeded catalogue data on migration rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [("products", "0008_seed_internal_materials")]

    operations = [migrations.RunPython(seed_creatives, preserve_catalog)]
