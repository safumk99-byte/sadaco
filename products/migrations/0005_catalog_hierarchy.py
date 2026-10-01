from django.db import migrations, models
import django.db.models.deletion


def seed_catalog(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")
    sections = {
        "WHITE ELEGANCE": [
            "Perfumes", "Cutpiece", "Shoe & Sandel", "Caps & Voil", "Inner wears", "Thobes",
        ],
        "CREATIVES": [
            "Wall Decors", "Mementoes", "Flex & Vinyl", "A3 Laser Printing", "Laser Cutting",
            "Graphic Designing", "A3, A4 Frames",
        ],
        "ROYAL LOOK": [
            "Suit Rental", "Jodhpuri", "Indo-Western", "Thobe Coat", "Dress Code",
            "Boots & Loafers", "Custom Stitching",
        ],
    }
    for section_name, children in sections.items():
        section, created = ProductCategory.objects.get_or_create(name=section_name, defaults={"is_active": True})
        if created or not section.products.exists():
            section.is_section = True
            section.parent = None
            section.is_active = True
            section.save(update_fields=["is_section", "parent", "is_active"])
        for child_name in children:
            child, created = ProductCategory.objects.get_or_create(name=child_name, defaults={"is_active": True})
            # Never move an existing product category that already contains products.
            if created or not child.products.exists():
                child.parent = section
                child.is_section = False
                child.is_active = True
                child.save(update_fields=["parent", "is_section", "is_active"])
    mementoes = ProductCategory.objects.filter(name="Mementoes").first()
    if mementoes:
        for name in ("First Prize", "Second Prize", "Third Prize", "Wedding Mementoes", "Other Mementoes"):
            child, _ = ProductCategory.objects.get_or_create(name=name, defaults={"is_active": True})
            if child.parent_id is None or child.parent_id == mementoes.pk:
                child.parent = mementoes
                child.is_section = False
                child.is_active = True
                child.save(update_fields=["parent", "is_section", "is_active"])
    thobes = ProductCategory.objects.filter(name="Thobes").first()
    if thobes:
        for name in ("Imarati", "Magribi"):
            child, created = ProductCategory.objects.get_or_create(name=name, defaults={"is_active": True})
            if created or not child.products.exists():
                child.parent = thobes
                child.is_section = False
                child.is_active = True
                child.save(update_fields=["parent", "is_section", "is_active"])


def unseed_catalog(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")
    names = [
        "WHITE ELEGANCE", "CREATIVES", "ROYAL LOOK", "Perfumes", "Cutpiece", "Shoe & Sandel",
        "Caps & Voil", "Inner wears", "Thobes", "Imarati", "Magribi", "Wall Decors", "Mementoes",
        "Flex & Vinyl", "A3 Laser Printing", "Laser Cutting", "Graphic Designing", "A3, A4 Frames",
        "Suit Rental", "Jodhpuri", "Indo-Western", "Thobe Coat", "Dress Code", "Boots & Loafers",
        "Custom Stitching", "First Prize", "Second Prize", "Third Prize", "Wedding Mementoes", "Other Mementoes",
    ]
    # Only remove seeded categories that are still unused; never delete customer/product data.
    for obj in ProductCategory.objects.filter(name__in=names):
        if not obj.products.exists():
            obj.delete()


class Migration(migrations.Migration):
    dependencies = [("products", "0004_customer_pricing")]
    operations = [
        migrations.AddField(
            model_name="productcategory",
            name="parent",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="products.productcategory"),
        ),
        migrations.AddField(
            model_name="productcategory",
            name="is_section",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(seed_catalog, unseed_catalog),
    ]
