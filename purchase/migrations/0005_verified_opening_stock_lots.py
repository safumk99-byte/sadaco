# Add verified opening-stock cost batches without inventing historical rates.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_offcut_discard_writeoff"),
        ("purchase", "0004_material_stock_lot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="materialstocklot",
            name="receipt_line",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="stock_lot", to="purchase.goodsreceiptline",
            ),
        ),
        migrations.AddField(
            model_name="materialstocklot",
            name="opening_movement",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="opening_cost_lot", to="inventory.materialstockmovement",
            ),
        ),
        migrations.AddField(
            model_name="materialstocklot",
            name="cost_source_reference",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddConstraint(
            model_name="materialstocklot",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(receipt_line__isnull=False, opening_movement__isnull=True)
                    | models.Q(receipt_line__isnull=True, opening_movement__isnull=False)
                ),
                name="purch_lot_exactly_one_source",
            ),
        ),
    ]
