from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0009_quotation_workflow_foundation"),
        ("products", "0013_configurable_labour_hours"),
    ]

    operations = [
        migrations.AddField(
            model_name="quotation",
            name="product",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quotations", to="products.product"),
        ),
    ]
