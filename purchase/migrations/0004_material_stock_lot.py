# Generated for receipt-backed material stock lots.
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_material_stock_count"),
        ("purchase", "0003_goods_receipt_lines"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialStockLot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_quantity", models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0.001)])),
                ("remaining_quantity", models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cost_lots", to="inventory.materialstockbalance")),
                ("receipt_line", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="stock_lot", to="purchase.goodsreceiptline")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddIndex(
            model_name="materialstocklot",
            index=models.Index(fields=["balance", "remaining_quantity"], name="purch_lot_bal_rem_idx"),
        ),
    ]
