from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("production", "0002_material_usage_tracking"),
        ("products", "0013_configurable_labour_hours"),
        ("staff", "0002_staffprofile_department"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductionCostEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cost_type", models.CharField(choices=[("machine", "Machine / Operation"), ("labour", "Direct Labour")], max_length=12)),
                ("operation_snapshot", models.CharField(blank=True, max_length=30)),
                ("description", models.CharField(blank=True, max_length=180)),
                ("staff_name_snapshot", models.CharField(blank=True, max_length=180)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=14, validators=[MinValueValidator(Decimal("0.001"))])),
                ("unit", models.CharField(max_length=20)),
                ("unit_rate", models.DecimalField(decimal_places=6, max_digits=14, validators=[MinValueValidator(0)])),
                ("total_cost", models.DecimalField(decimal_places=2, max_digits=16, validators=[MinValueValidator(0)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="production_cost_entries", to=settings.AUTH_USER_MODEL)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cost_entries", to="production.productionjob")),
                ("machine_rate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="production_cost_entries", to="products.machinerate")),
                ("material_line", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cost_entries", to="production.productionmaterial")),
                ("staff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="production_cost_entries", to="staff.staffprofile")),
            ],
            options={"ordering": ["created_at", "pk"]},
        ),
        migrations.AddConstraint(
            model_name="productioncostentry",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(cost_type="machine", machine_rate__isnull=False, staff__isnull=True)
                    | models.Q(cost_type="labour", machine_rate__isnull=True, staff__isnull=False)
                ),
                name="prod_cost_entry_exactly_one_source",
            ),
        ),
    ]
