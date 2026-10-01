from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_stocktransaction"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="product",
                    name="actual_price",
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                    ),
                ),
                migrations.AddField(
                    model_name="product",
                    name="discount_price",
                    field=models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                    ),
                ),
                migrations.AddField(
                    model_name="product",
                    name="customer_visible",
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name="product",
                    name="image",
                    field=models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="products/%Y/%m/",
                    ),
                ),
            ],
        ),
    ]
