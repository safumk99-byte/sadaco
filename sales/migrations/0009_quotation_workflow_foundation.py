from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0008_customer_identity_and_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="quotation",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending_approval", "Pending Approval"),
                    ("sent", "Sent"),
                    ("accepted", "Accepted"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("expired", "Expired"),
                    ("converted", "Converted to Order"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(model_name="quotation", name="dimensions", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="quotation", name="discount_percent", field=models.DecimalField(decimal_places=2, default=0, max_digits=5, validators=[MinValueValidator(0), MaxValueValidator(100)])),
        migrations.AddField(model_name="quotation", name="discount_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[MinValueValidator(0)])),
        migrations.AddField(model_name="quotation", name="subtotal", field=models.DecimalField(decimal_places=2, default=0, max_digits=14, validators=[MinValueValidator(0)])),
        migrations.AddField(model_name="quotation", name="tax_rate", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])),
        migrations.AddField(model_name="quotation", name="tax_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[MinValueValidator(0)])),
        migrations.AddField(model_name="quotation", name="terms", field=models.TextField(blank=True)),
        migrations.AddField(model_name="quotation", name="approval_requested_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="approved_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="approval_notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="quotation", name="sent_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="rejected_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="company_details_snapshot", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(
            model_name="quotation",
            name="approved_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_quotations", to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name="QuotationConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_name", models.CharField(default="SADACO GROUP OF COMPANIES", max_length=180)),
                ("company_address", models.TextField(blank=True)),
                ("company_phone", models.CharField(blank=True, max_length=60)),
                ("company_email", models.EmailField(blank=True, max_length=254)),
                ("company_website", models.URLField(blank=True)),
                ("tax_label", models.CharField(blank=True, max_length=40)),
                ("tax_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ("manager_discount_limit_percent", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])),
                ("default_terms", models.TextField(blank=True)),
                ("default_validity_days", models.PositiveIntegerField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_quotation_configurations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Quotation Configuration", "verbose_name_plural": "Quotation Configuration"},
        ),
        migrations.CreateModel(
            name="QuotationLineItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("material", "Material"), ("labour", "Labour"), ("machine", "Machine"), ("finishing", "Finishing"), ("packing", "Packing"), ("delivery_installation", "Delivery / Installation")], max_length=32)),
                ("description", models.CharField(max_length=255)),
                ("dimensions", models.CharField(blank=True, max_length=180)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12, validators=[MinValueValidator(0)])),
                ("unit", models.CharField(blank=True, max_length=40)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(0)])),
                ("line_total", models.DecimalField(decimal_places=2, default=0, max_digits=14, validators=[MinValueValidator(0)])),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("quotation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="line_items", to="sales.quotation")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="QuotationApproval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("requested", "Approval Requested"), ("approved", "Approved"), ("rejected", "Rejected")], max_length=20)),
                ("discount_percent", models.DecimalField(decimal_places=2, max_digits=5)),
                ("discount_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quotation_approval_actions", to=settings.AUTH_USER_MODEL)),
                ("quotation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="approval_history", to="sales.quotation")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
