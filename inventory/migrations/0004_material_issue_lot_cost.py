# Generated for receipt-backed issue costing.
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_material_stock_count"),
        ("purchase", "0004_material_stock_lot"),
    ]

    operations = [
        migrations.AddField(
            model_name="materialissue",
            name="stock_lot",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="issues", to="purchase.materialstocklot"),
        ),
        migrations.AddField(
            model_name="materialissue",
            name="unit_rate",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="materialissue",
            name="stock_movement",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="material_issue", to="inventory.materialstockmovement"),
        ),
    ]
