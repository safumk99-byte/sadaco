# Generated for the final SADACO material-inventory requirements.
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_department"),
        ("products", "0013_configurable_labour_hours"),
        ("production", "0001_initial"),
        ("sales", "0007_customer_department"),
        ("staff", "0001_initial"),
        ("inventory", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialStockBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location", models.CharField(max_length=160)),
                ("quantity", models.DecimalField(decimal_places=3, default=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("minimum_quantity", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="material_stock_balances", to="core.department")),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_balances", to="products.materialvariant")),
            ],
            options={"ordering":["department__name","location","material__material_name"]},
        ),
        migrations.AddConstraint(model_name="materialstockbalance", constraint=models.UniqueConstraint(fields=("material","department","location"), name="inv_material_dept_location_uniq")),
        migrations.AddIndex(model_name="materialstockbalance", index=models.Index(fields=["department","location"], name="inventory_m_department_3a0d4f_idx")),
        migrations.CreateModel(
            name="MaterialStockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("movement_type", models.CharField(choices=[("opening","Opening"),("purchase_receipt","Purchase Receipt"),("job_issue","Job Issue"),("return","Return"),("offcut_in","Reusable Offcut"),("wastage","Wastage"),("closing","Closing"),("correction","Authorized Correction")], max_length=24)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0.001)])),
                ("balance_after", models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movements", to="inventory.materialstockbalance")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="material_stock_movements", to=settings.AUTH_USER_MODEL)),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="material_stock_movements", to="staff.staffprofile")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="material_stock_movements", to="production.productionjob")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="material_stock_movements", to="sales.salesorder")),
            ],
            options={"ordering":["-created_at"]},
        ),
        migrations.AddIndex(model_name="materialstockmovement", index=models.Index(fields=["balance","-created_at"], name="inventory_m_balance_6e36c4_idx")),
        migrations.AddIndex(model_name="materialstockmovement", index=models.Index(fields=["movement_type","-created_at"], name="inventory_m_movement_42d4aa_idx")),
        migrations.CreateModel(
            name="ReusableOffcut",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location", models.CharField(max_length=160)),
                ("thickness_mm", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("length_mm", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ("width_mm", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ("usable_area_sqft", models.DecimalField(decimal_places=4, max_digits=12, validators=[django.core.validators.MinValueValidator(0.0001)])),
                ("status", models.CharField(choices=[("available","Available"),("used","Used"),("discarded","Discarded")], default="available", max_length=16)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reusable_offcuts", to="core.department")),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reusable_offcuts", to="products.materialvariant")),
                ("source_job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generated_offcuts", to="production.productionjob")),
                ("used_for_job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="used_offcuts", to="production.productionjob")),
            ],
            options={"ordering":["-created_at"]},
        ),
        migrations.AddIndex(model_name="reusableoffcut", index=models.Index(fields=["department","status"], name="inventory_r_department_0b3b92_idx")),
    ]
