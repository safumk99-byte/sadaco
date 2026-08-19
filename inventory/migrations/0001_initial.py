from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("production", "0001_initial"),
        ("products", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialIssue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0.01)])),
                ("status", models.CharField(choices=[("draft","Draft"),("issued","Issued"),("cancelled","Cancelled")], default="issued", max_length=20)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("remarks", models.TextField(blank=True)),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("issued_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="material_issues", to=settings.AUTH_USER_MODEL)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="material_issues", to="production.productionjob")),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_issues", to="production.productionmaterial")),
            ],
            options={"ordering":["-issued_at"],"indexes":[
                models.Index(fields=["job","status"], name="inventory_mi_job_id_5e5d22_idx"),
                models.Index(fields=["material","status"], name="inventory_mi_material_2c3f1d_idx"),
            ]},
        ),
        migrations.CreateModel(
            name="StockCount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("system_quantity", models.DecimalField(decimal_places=2, max_digits=12)),
                ("counted_quantity", models.DecimalField(decimal_places=2, max_digits=12)),
                ("variance", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reason", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("open","Open"),("completed","Completed")], default="completed", max_length=20)),
                ("counted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("counted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_counts", to=settings.AUTH_USER_MODEL)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_counts", to="products.product")),
            ],
            options={"ordering":["-counted_at"],"indexes":[
                models.Index(fields=["product","-counted_at"], name="inventory_sc_product_6f2b51_idx"),
            ]},
        ),
        migrations.CreateModel(
            name="ReorderAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_open", models.BooleanField(default=True)),
                ("last_notified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_reorder_alert", to="products.product")),
            ],
        ),
    ]
