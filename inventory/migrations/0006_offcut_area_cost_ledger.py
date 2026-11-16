# Source-batch traceability and a separate square-foot consumption ledger for reusable offcuts.
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0005_material_issue_usage_attribution"),
        ("purchase", "0004_material_stock_lot"),
        ("production", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="reusableoffcut",
            name="source_issue",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generated_offcuts", to="inventory.materialissue"),
        ),
        migrations.AddField(
            model_name="reusableoffcut",
            name="source_lot",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generated_offcuts", to="purchase.materialstocklot"),
        ),
        migrations.AddField(
            model_name="reusableoffcut",
            name="cost_per_sqft",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.CreateModel(
            name="OffcutUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("used_area_sqft", models.DecimalField(decimal_places=4, max_digits=12, validators=[django.core.validators.MinValueValidator(0.0001)])),
                ("cost_per_sqft", models.DecimalField(decimal_places=6, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("total_cost", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("offcut", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="usages", to="inventory.reusableoffcut")),
                ("target_job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="offcut_usages", to="production.productionjob")),
                ("target_material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="offcut_usages", to="production.productionmaterial")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="offcutusage",
            index=models.Index(fields=["target_job", "created_at"], name="inv_offcut_job_created_idx"),
        ),
    ]
