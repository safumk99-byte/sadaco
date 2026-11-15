from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0012_remove_demo_operational_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffcompensation",
            name="working_days_per_month",
            field=models.PositiveSmallIntegerField(default=26),
        ),
        migrations.AddField(
            model_name="staffcompensation",
            name="productive_hours_per_day",
            field=models.DecimalField(decimal_places=2, default=Decimal("8.25"), max_digits=5),
        ),
    ]
