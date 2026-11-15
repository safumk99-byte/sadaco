from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("inventory", "0002_material_stock_ledger"),
        ("products", "0013_configurable_labour_hours"),
        ("purchase", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorder",
            name="department",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="purchase_orders", to="core.department",
            ),
        ),
        migrations.AlterField(
            model_name="purchaseitem",
            name="product",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="purchase_items", to="products.product",
            ),
        ),
        migrations.AddField(
            model_name="purchaseitem",
            name="material_variant",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="purchase_items", to="products.materialvariant",
            ),
        ),
    ]
