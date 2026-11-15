from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# Only values explicitly supplied in the approved SADACO requirements are seeded.
# Missing rates remain NULL; no retail rates are inferred.
MATERIALS = [
    # Astari Acrylic, 8x4 ft. Thickness and code are kept as separate variants.
    ("Acrylic", "Astari", "1.80", "402", "colour", "3085.00", None, 8, 4),
    ("Acrylic", "Astari", "1.80", "434", "colour", "3085.00", None, 8, 4),
    ("Acrylic", "Astari", "1.80", "441", "colour", "3160.00", None, 8, 4),
    ("Acrylic", "Astari", "1.80", "136 / 502", "colour", "3085.00", None, 8, 4),
    ("Acrylic", "Astari", "1.80", "Others", "clear", "2950.00", None, 8, 4),
    ("Acrylic", "Astari", "1.80", "Others", "colour", "3050.00", None, 8, 4),
    ("Acrylic", "Astari", "2.50", "", "clear", "3812.00", None, 8, 4),
    ("Acrylic", "Astari", "2.50", "", "colour", "3864.00", None, 8, 4),
    ("Acrylic", "Astari", "2.70", "", "clear", "4368.00", None, 8, 4),
    ("Acrylic", "Astari", "2.70", "", "colour", "4440.00", None, 8, 4),
    ("Acrylic", "Astari", "3.50", "", "clear", "4960.00", None, 8, 4),
    ("Acrylic", "Astari", "3.50", "", "colour", "5152.00", None, 8, 4),
    ("Acrylic", "Astari", "3.70", "", "clear", "5529.00", None, 8, 4),
    ("Acrylic", "Astari", "3.70", "", "colour", "5920.00", None, 8, 4),
    ("Acrylic", "Astari", "4.50", "", "clear", "6200.00", None, 8, 4),
    ("Acrylic", "Astari", "4.50", "", "colour", "6340.00", None, 8, 4),
    ("Acrylic", "Astari", "4.80", "", "clear", "7040.00", None, 8, 4),
    ("Acrylic", "Astari", "4.80", "", "colour", "7400.00", None, 8, 4),
    ("Acrylic", "Astari", "5.50", "", "clear", "7622.00", None, 8, 4),
    ("Acrylic", "Astari", "5.50", "", "colour", "7728.00", None, 8, 4),
    ("Acrylic", "Astari", "5.80", "", "clear", "8448.00", None, 8, 4),
    ("Acrylic", "Astari", "5.80", "", "colour", "8880.00", None, 8, 4),
    ("Acrylic", "Astari", "6.80", "", "clear", "9856.00", None, 8, 4),
    ("Acrylic", "Astari", "6.80", "", "colour", "10360.00", None, 8, 4),
    ("Acrylic", "Astari", "7.80", "", "clear", "11264.00", None, 8, 4),
    ("Acrylic", "Astari", "7.80", "", "colour", "11840.00", None, 8, 4),

    # Otherbrand is intentionally generic; 8x4 ft.
    *[
        ("Acrylic", "Otherbrand", thickness, "", colour, rate, None, 8, 4)
        for thickness, clear, colour_rate in [
            ("2.00", "2550.00", "2650.00"),
            ("3.00", "3552.00", "3648.00"),
            ("4.00", "4736.00", "4864.00"),
            ("5.00", "5920.00", "6080.00"),
            ("6.00", "7104.00", "7296.00"),
            ("7.00", "8288.00", "8512.00"),
            ("8.00", "9472.00", "9728.00"),
        ]
        for colour, rate in [("clear", clear), ("colour", colour_rate)]
    ],

    # Indian sheet, 4x3 ft. Retail values were not supplied.
    *[
        ("Acrylic", "", thickness, "", "na", rate, None, 4, 3)
        for thickness, rate in [
            ("2.00", "455.00"), ("3.00", "560.00"), ("4.00", "796.00"),
            ("5.00", "1060.00"), ("6.00", "1200.00"),
        ]
    ],

    # Mirror sheet, 8x4 ft. Retail values were not supplied.
    ("Mirror Sheet", "", None, "Gold / Silver Gum", "na", "1980.00", None, 8, 4),
    ("Mirror Sheet", "", None, "Rose / Copper Gum", "na", "2100.00", None, 8, 4),
    ("Mirror Sheet", "", "2.00", "Gold / Silver", "na", "2200.00", None, 8, 4),
    ("Mirror Sheet", "", "3.00", "Gold / Silver", "na", "2900.00", None, 8, 4),
    ("Mirror Sheet", "", None, "Brush Gold / Silver", "na", "640.00", None, 8, 4),
]


def seed_materials_and_machine_rates(apps, schema_editor):
    MaterialVariant = apps.get_model("products", "MaterialVariant")
    MachineRate = apps.get_model("products", "MachineRate")

    for material, brand, thickness, variant, colour, purchase, retail, width, height in MATERIALS:
        lookup = {
            "material_name": material,
            "brand": brand,
            "thickness_mm": Decimal(thickness) if thickness else None,
            "variant": variant,
            "colour": colour,
        }
        MaterialVariant.objects.get_or_create(
            **lookup,
            defaults={
                "sheet_width_ft": Decimal(width),
                "sheet_height_ft": Decimal(height),
                "purchase_rate": Decimal(purchase) if purchase is not None else None,
                "retail_rate": Decimal(retail) if retail is not None else None,
                "unit": "Sheet",
                "is_active": True,
            },
        )

    machine_rates = [
        ("laser_cutting", "", None, "20.00", "minute"),
        ("laser_engraving", "", None, "25.00", "minute"),
        ("cnc_cutting", "Multy Wood", "5.00", "50.00", "sq_ft"),
        ("cnc_cutting", "Multy Wood", "6.00", "50.00", "sq_ft"),
        ("cnc_cutting", "Multy Wood", "8.00", "60.00", "sq_ft"),
    ]
    for operation, material, thickness, rate, unit in machine_rates:
        lookup = {
            "operation": operation,
            "material_name": material,
            "thickness_mm": Decimal(thickness) if thickness else None,
            "unit": unit,
        }
        MachineRate.objects.get_or_create(**lookup, defaults={"rate": Decimal(rate), "is_active": True})


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0009_creatives_catalog_structure"),
        ("staff", "0002_staffprofile_department"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("material_name", models.CharField(max_length=120)),
                ("brand", models.CharField(blank=True, max_length=120)),
                ("thickness_mm", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("variant", models.CharField(blank=True, max_length=120)),
                ("colour", models.CharField(choices=[("clear", "Clear"), ("colour", "Colour"), ("na", "Not applicable")], default="na", max_length=12)),
                ("sheet_width_ft", models.DecimalField(decimal_places=2, default=8, max_digits=7)),
                ("sheet_height_ft", models.DecimalField(decimal_places=2, default=4, max_digits=7)),
                ("purchase_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("retail_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("supplier_name", models.CharField(blank=True, max_length=180)),
                ("stock_quantity", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("unit", models.CharField(default="Sheet", max_length=30)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["material_name", "brand", "thickness_mm", "variant", "colour"]},
        ),
        migrations.AddConstraint(
            model_name="materialvariant",
            constraint=models.UniqueConstraint(fields=("material_name", "brand", "thickness_mm", "variant", "colour"), name="products_material_variant_unique"),
        ),
        migrations.CreateModel(
            name="MaterialRateHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purchase_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("retail_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("effective_from", models.DateField()),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rate_history", to="products.materialvariant")),
            ],
            options={"ordering": ["-effective_from", "-created_at"]},
        ),
        migrations.CreateModel(
            name="MachineRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(choices=[("laser_cutting", "Laser Cutting"), ("laser_engraving", "Laser Engraving"), ("cnc_cutting", "CNC Cutting")], max_length=30)),
                ("material_name", models.CharField(blank=True, max_length=120)),
                ("thickness_mm", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("rate", models.DecimalField(decimal_places=2, max_digits=12)),
                ("unit", models.CharField(default="minute", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["operation", "material_name", "thickness_mm"]},
        ),
        migrations.CreateModel(
            name="StaffCompensation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_type", models.CharField(choices=[("monthly", "Monthly Salary"), ("per_work", "Work-based Payment")], max_length=20)),
                ("monthly_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("working_days_per_month", models.PositiveSmallIntegerField(default=26)),
                ("productive_hours_per_day", models.DecimalField(decimal_places=2, default=Decimal("8.25"), max_digits=5)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("staff", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="compensation", to="staff.staffprofile")),
            ],
        ),
        migrations.RunPython(seed_materials_and_machine_rates, migrations.RunPython.noop),
    ]
