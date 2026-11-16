# Issue-level return and wastage attribution for receipt-batch costing.
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0004_material_issue_lot_cost"),
    ]

    operations = [
        migrations.AddField(
            model_name="materialissue",
            name="returned_quantity",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="materialissue",
            name="wastage_quantity",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="materialstockmovement",
            name="source_issue",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="usage_movements", to="inventory.materialissue"),
        ),
    ]
