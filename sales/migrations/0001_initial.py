from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("staff", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)), ("phone", models.CharField(max_length=30)),
                ("alternate_phone", models.CharField(blank=True, max_length=30)), ("email", models.EmailField(blank=True, max_length=254)),
                ("address", models.TextField(blank=True)), ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive")], default="active", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ], options={"ordering": ["name"], "indexes": [models.Index(fields=["phone"], name="sales_cust_phone_0c6a6b_idx"), models.Index(fields=["status"], name="sales_cust_status_2e5a25_idx")]},
        ),
        migrations.CreateModel(
            name="Enquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enquiry_no", models.CharField(editable=False, max_length=30, unique=True)),
                ("channel", models.CharField(choices=[("phone", "Phone"), ("whatsapp", "WhatsApp"), ("instagram", "Instagram"), ("facebook", "Facebook"), ("walk_in", "Walk-in"), ("referral", "Referral"), ("other", "Other")], max_length=20)),
                ("product_type", models.CharField(max_length=180)), ("quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("design_reference", models.CharField(blank=True, max_length=255)), ("deadline", models.DateField(blank=True, null=True)), ("budget_range", models.CharField(blank=True, max_length=120)), ("expected_delivery_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("new", "New"), ("contacted", "Contacted"), ("quotation", "Quotation Prepared"), ("converted", "Converted to Order"), ("lost", "Lost")], default="new", max_length=20)),
                ("requirement", models.TextField(blank=True)), ("response_time_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales_enquiries", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_sales_enquiries", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enquiries", to="sales.customer")),
            ], options={"ordering": ["-created_at"], "indexes": [models.Index(fields=["status", "created_at"], name="sales_enq_status_6d4d6f_idx"), models.Index(fields=["customer", "status"], name="sales_enq_customer_1e2c62_idx")]},
        ),
        migrations.CreateModel(
            name="Quotation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("quotation_no", models.CharField(editable=False, max_length=30, unique=True)),
                ("item_description", models.CharField(max_length=255)), ("quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("material_cost", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("labour_cost", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("machine_cost", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("finishing_cost", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("packaging_cost", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("delivery_cost", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("quoted_price", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("delivery_timeline", models.CharField(blank=True, max_length=180)), ("advance_required", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("valid_until", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent"), ("approved", "Approved"), ("rejected", "Rejected"), ("expired", "Expired"), ("converted", "Converted to Order")], default="draft", max_length=20)), ("notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quotations", to="sales.customer")), ("enquiry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quotations", to="sales.enquiry")), ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_quotations", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-created_at"], "indexes": [models.Index(fields=["status", "created_at"], name="sales_quo_status_3d7c9d_idx"), models.Index(fields=["customer", "status"], name="sales_quo_customer_6e3c5b_idx")]},
        ),
        migrations.CreateModel(
            name="SalesOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("order_no", models.CharField(editable=False, max_length=30, unique=True)),
                ("item_description", models.CharField(max_length=255)), ("quantity", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("confirmed_price", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])), ("design_reference", models.CharField(blank=True, max_length=255)), ("delivery_date", models.DateField(blank=True, null=True)), ("deadline", models.DateField(blank=True, null=True)), ("advance_required", models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("status", models.CharField(choices=[("confirmed", "Confirmed"), ("design_pending", "Design Pending"), ("production_pending", "Production Pending"), ("in_production", "In Production"), ("ready", "Ready"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="confirmed", max_length=30)), ("notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="sales.customer")), ("quotation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="sales.quotation")), ("responsible_staff", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales_orders", to="staff.staffprofile")), ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_sales_orders", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-created_at"], "indexes": [models.Index(fields=["status", "delivery_date"], name="sales_ord_status_9d5f0b_idx"), models.Index(fields=["customer", "status"], name="sales_ord_customer_1a0d6a_idx")]},
        ),
    ]
