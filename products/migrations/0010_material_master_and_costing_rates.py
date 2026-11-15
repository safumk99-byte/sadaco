from decimal import Decimal
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


def seed_material_master(apps, schema_editor):
    Material = apps.get_model("products", "MaterialVariant")
    MaterialRateHistory = apps.get_model("products", "MaterialRateHistory")
    MachineRate = apps.get_model("products", "MachineRate")

    def add(name, brand="", thickness=None, variant="", colour="na", width="8", height="4", rate=None):
        material, _ = Material.objects.update_or_create(
            material_name=name, brand=brand, thickness_mm=Decimal(str(thickness)) if thickness is not None else None,
            variant=variant, colour=colour,
            defaults={
                "sheet_width_ft": Decimal(width), "sheet_height_ft": Decimal(height),
                "purchase_rate": Decimal(str(rate)) if rate is not None else None,
                "retail_rate": None, "unit": "Sheet", "stock_quantity": Decimal("0"), "is_active": True,
            },
        )
        if rate is not None:
            MaterialRateHistory.objects.get_or_create(
                material_id=material.pk,
                effective_from=timezone.localdate(),
                defaults={
                    "purchase_rate": material.purchase_rate,
                    "retail_rate": material.retail_rate,
                    "note": "Initial rate from approved SADACO requirements",
                },
            )

    # ASTARI acrylic, 8 x 4 ft sheets. 1.8mm supplier variants are distinct names.
    for variant, rate in [("402", 3085), ("434", 3085), ("441", 3160), ("136", 3085), ("502", 3085)]:
        add("Acrylic Sheet", "Astari", "1.8", variant, "colour", rate=rate)
    add("Acrylic Sheet", "Astari", "1.8", "Others", "clear", rate=2950)
    add("Acrylic Sheet", "Astari", "1.8", "Others", "colour", rate=3050)
    astari = [
        ("2.5",3812,3864),("2.7",4368,4440),("3.5",4960,5152),("3.7",5529,5920),
        ("4.5",6200,6340),("4.8",7040,7400),("5.5",7622,7728),("5.8",8448,8880),
        ("6.8",9856,10360),("7.8",11264,11840),
    ]
    for thickness, clear, colour in astari:
        add("Acrylic Sheet", "Astari", thickness, "", "clear", rate=clear)
        add("Acrylic Sheet", "Astari", thickness, "", "colour", rate=colour)

    # Other-brand acrylic, 8 x 4 ft.
    for thickness, clear, colour in [
        ("2",2550,2650),("3",3552,3648),("4",4736,4864),("5",5920,6080),
        ("6",7104,7296),("7",8288,8512),("8",9472,9728),
    ]:
        add("Acrylic Sheet", "Otherbrand", thickness, "", "clear", rate=clear)
        add("Acrylic Sheet", "Otherbrand", thickness, "", "colour", rate=colour)

    # Indian Sheet, 4 x 3 ft; no brand and no retail rate supplied.
    for thickness, rate in [("2",455),("3",560),("4",796),("5",1060),("6",1200)]:
        add("Indian Sheet", "", thickness, "", "na", "4", "3", rate)

    # Mirror sheet, 8 x 4 ft. Thickness is left blank where the source did not specify it.
    for variant, rate in [
        ("Gold / Silver Gum",1980),("Rose / Copper Gum",2100),
        ("2mm Gold / Silver",2200),("3mm Gold / Silver",2900),
        ("Brush Gold / Silver",640),
    ]:
        add("Mirror Sheet", "", None, variant, "na", rate=rate)

    for operation, rate, unit, material, thickness in [
        ("laser_cutting",20,"minute","",None),
        ("laser_engraving",25,"minute","",None),
        ("cnc_cutting",50,"sqft","Multy Wood","5"),
        ("cnc_cutting",50,"sqft","Multy Wood","6"),
        ("cnc_cutting",60,"sqft","Multy Wood","8"),
    ]:
        MachineRate.objects.update_or_create(
            operation=operation, material_name=material,
            thickness_mm=Decimal(thickness) if thickness else None,
            defaults={"rate": Decimal(rate), "unit": unit, "is_active": True},
        )


def preserve_seeded_rates(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0009_creatives_catalog_structure"),
        ("staff", "0002_staffprofile_department"),
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
                ("colour", models.CharField(choices=[("clear","Clear"),("colour","Colour"),("na","Not applicable")], default="na", max_length=12)),
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
            options={"ordering":["material_name","brand","thickness_mm","variant","colour"]},
        ),
        migrations.AddConstraint(
            model_name="materialvariant",
            constraint=models.UniqueConstraint(fields=("material_name","brand","thickness_mm","variant","colour"), name="products_material_variant_unique"),
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
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="auth.user")),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rate_history", to="products.materialvariant")),
            ],
            options={"ordering":["-effective_from","-created_at"]},
        ),
        migrations.CreateModel(
            name="MachineRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(choices=[("laser_cutting","Laser Cutting"),("laser_engraving","Laser Engraving"),("cnc_cutting","CNC Cutting")], max_length=30)),
                ("material_name", models.CharField(blank=True, max_length=120)),
                ("thickness_mm", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("rate", models.DecimalField(decimal_places=2, max_digits=12)),
                ("unit", models.CharField(default="minute", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering":["operation","material_name","thickness_mm"]},
        ),
        migrations.CreateModel(
            name="StaffCompensation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_type", models.CharField(choices=[("monthly","Monthly Salary"),("per_work","Work-based Payment")], max_length=20)),
                ("monthly_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("staff", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="compensation", to="staff.staffprofile")),
            ],
        ),
        migrations.RunPython(seed_material_master, preserve_seeded_rates),
    ]
