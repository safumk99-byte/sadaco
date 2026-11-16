# Preserve the value of offcut area written off when a reusable piece is discarded.
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0006_offcut_area_cost_ledger")]

    operations = [
        migrations.AddField(
            model_name="reusableoffcut",
            name="discarded_area_sqft",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name="reusableoffcut",
            name="discarded_cost",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
