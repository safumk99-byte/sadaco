from django.db import migrations, models


def ensure_customer_catalog_columns(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Product._meta.db_table
            )
        }

    missing_fields = [
        ("actual_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        ("discount_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        ("customer_visible", models.BooleanField(default=False)),
        ("image", models.ImageField(blank=True, null=True, upload_to="products/%Y/%m/")),
    ]
    for name, field in missing_fields:
        if name not in existing:
            field.contribute_to_class(Product, name)
            schema_editor.add_field(Product, field)


def preserve_customer_catalog_columns(apps, schema_editor):
    # Keep these columns on rollback: existing customer catalogue data may use them.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_stocktransaction"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_customer_catalog_columns,
                    preserve_customer_catalog_columns,
                ),
            ],
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
