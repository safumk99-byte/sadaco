from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_material_stock_ledger"),
        ("products", "0013_configurable_labour_hours"),
        ("production", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="productionmaterial",
            name="material_variant",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="production_requirements", to="products.materialvariant",
            ),
        ),
        migrations.AddField(
            model_name="productionmaterial",
            name="returned_quantity",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="productionmaterial",
            name="wastage_quantity",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="productionmaterial",
            name="issue_unit_rate",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
    ]
