from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0012_salesorder_payment_exceptions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="salesorder",
            name="closed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="salesorder",
            name="closed_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="closed_sales_orders", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="salesorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("confirmed", "Confirmed"), ("design_pending", "Design Pending"),
                    ("production_pending", "Production Pending"), ("in_production", "In Production"),
                    ("ready", "Ready"), ("delivered", "Delivered"), ("closed", "Closed"),
                    ("cancelled", "Cancelled"),
                ],
                default="confirmed", max_length=30,
            ),
        ),
    ]
