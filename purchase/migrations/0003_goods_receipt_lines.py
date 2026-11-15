from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_material_stock_count"),
        ("purchase", "0002_department_material_purchasing"),
    ]

    operations = [
        migrations.CreateModel(
            name="GoodsReceiptLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("received_quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0.01)])),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("material_stock_movement", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_receipt_line", to="inventory.materialstockmovement")),
                ("purchase_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receipt_lines", to="purchase.purchaseitem")),
                ("receipt", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="purchase.goodsreceipt")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="goodsreceiptline",
            constraint=models.UniqueConstraint(fields=("receipt", "purchase_item"), name="purchase_receipt_item_uniq"),
        ),
    ]
