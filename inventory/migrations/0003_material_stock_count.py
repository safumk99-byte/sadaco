from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_material_stock_ledger"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialStockCount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("system_quantity", models.DecimalField(decimal_places=3, max_digits=14)),
                ("counted_quantity", models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ("variance", models.DecimalField(decimal_places=3, max_digits=14)),
                ("status", models.CharField(choices=[("pending","Pending Review"),("approved","Approved"),("rejected","Rejected")], default="pending", max_length=16)),
                ("reason", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("balance", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="physical_counts", to="inventory.materialstockbalance")),
                ("correction_movement", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="physical_count", to="inventory.materialstockmovement")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="material_counts_reviewed", to=settings.AUTH_USER_MODEL)),
                ("submitted_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="material_counts_submitted", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="materialstockcount",
            index=models.Index(fields=["status","-created_at"], name="inventory_m_status_9f7a1b_idx"),
        ),
    ]
