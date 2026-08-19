from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0003_customer_sales_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="quotation",
            name="order_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="quotations",
                to="sales.orderrequest",
            ),
        ),
    ]
