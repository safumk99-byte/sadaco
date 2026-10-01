from django.db import migrations, models
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):
    dependencies = [("products", "0006_remove_white_elegance")]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="selling_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
