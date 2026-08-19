from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0002_customer_portal"),
    ]

    operations = [
        migrations.CreateModel(
            name="DesignApproval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField(default=1)),
                ("file", models.FileField(blank=True, null=True, upload_to="designs/%Y/%m/")),
                ("notes", models.TextField(blank=True)),
                ("customer_notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent to Customer"), ("revision", "Revision Requested"), ("approved", "Approved"), ("rejected", "Rejected")], default="draft", max_length=20)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_designs", to=settings.AUTH_USER_MODEL)),
                ("quotation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="designs", to="sales.quotation")),
            ],
            options={"ordering": ["-version", "-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="designapproval",
            constraint=models.UniqueConstraint(fields=("quotation", "version"), name="sales_design_quotation_version_uniq"),
        ),
        migrations.CreateModel(
            name="PaymentRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_type", models.CharField(choices=[("advance", "Advance"), ("final", "Final"), ("other", "Other")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("paid_on", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("received", "Received"), ("verified", "Verified"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_sales_payments", to=settings.AUTH_USER_MODEL)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="sales.salesorder")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DeliveryRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delivery_date", models.DateField(blank=True, null=True)),
                ("address", models.TextField(blank=True)),
                ("transport", models.CharField(blank=True, max_length=120)),
                ("responsible_person", models.CharField(blank=True, max_length=180)),
                ("installation_required", models.BooleanField(default=False)),
                ("installation_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("scheduled", "Scheduled"), ("ready", "Ready for Delivery"), ("out", "Out for Delivery"), ("delivered", "Delivered"), ("installed", "Installed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("acknowledgement", models.TextField(blank=True)),
                ("completion_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="delivery", to="sales.salesorder")),
            ],
        ),
        migrations.CreateModel(
            name="CustomerFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("comment", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="feedback", to="sales.salesorder")),
            ],
        ),
    ]
