from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("products", "0002_stocktransaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="user",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="customer_profile", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.CreateModel(
            name="OrderRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_no", models.CharField(editable=False, max_length=30, unique=True)),
                ("request_type", models.CharField(choices=[("enquiry", "Enquiry"), ("order_request", "Order Request")], default="enquiry", max_length=20)),
                ("product_name", models.CharField(blank=True, max_length=180)),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("size", models.CharField(blank=True, max_length=120)),
                ("material_preference", models.CharField(blank=True, max_length=180)),
                ("requirement", models.TextField()),
                ("budget", models.CharField(blank=True, max_length=120)),
                ("requested_date", models.DateField(blank=True, null=True)),
                ("design_requirement", models.TextField(blank=True)),
                ("reference_file", models.FileField(blank=True, null=True, upload_to="customer_requests/%Y/%m/")),
                ("status", models.CharField(choices=[("new", "New"), ("reviewing", "Under Review"), ("contacted", "Customer Contacted"), ("quotation", "Quotation in Progress"), ("confirmed", "Confirmed"), ("declined", "Declined"), ("cancelled", "Cancelled")], default="new", max_length=30)),
                ("manager_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_customer_requests", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_requests", to="sales.customer")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_order_requests", to="products.product")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="orderrequest",
            index=models.Index(fields=["status", "created_at"], name="sales_order_status_2d6a1c_idx"),
        ),
        migrations.AddIndex(
            model_name="orderrequest",
            index=models.Index(fields=["customer", "status"], name="sales_order_customer_6b2b6d_idx"),
        ),
        migrations.CreateModel(
            name="CustomerNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("request", "New Request"), ("quotation", "Quotation"), ("order", "Order"), ("message", "Message"), ("status", "Status Update")], max_length=20)),
                ("title", models.CharField(max_length=180)),
                ("message", models.TextField()),
                ("url", models.CharField(blank=True, max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="customernotification",
            index=models.Index(fields=["user", "is_read", "created_at"], name="sales_notif_user_9d7e6b_idx"),
        ),
    ]
