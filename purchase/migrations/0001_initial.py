from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial=True
    dependencies=[("products","0002_stocktransaction"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("name",models.CharField(max_length=180)),("contact_person",models.CharField(blank=True,max_length=180)),
                ("phone",models.CharField(blank=True,max_length=30)),("email",models.EmailField(blank=True,max_length=254)),
                ("address",models.TextField(blank=True)),("tax_number",models.CharField(blank=True,max_length=80)),
                ("payment_terms",models.CharField(blank=True,max_length=120)),("notes",models.TextField(blank=True)),
                ("status",models.CharField(choices=[("active","Active"),("inactive","Inactive")],default="active",max_length=20)),
                ("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
            ],options={"ordering":["name"],"indexes":[models.Index(fields=["status","name"],name="purchase_su_status_5b5f2d_idx")]}
        ),
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("po_no",models.CharField(editable=False,max_length=30,unique=True)),("order_date",models.DateField(default=django.utils.timezone.localdate)),
                ("expected_date",models.DateField(blank=True,null=True)),("status",models.CharField(choices=[("draft","Draft"),("sent","Sent to Supplier"),("partial","Partially Received"),("received","Received"),("cancelled","Cancelled")],default="draft",max_length=20)),
                ("notes",models.TextField(blank=True)),("subtotal",models.DecimalField(decimal_places=2,default=0,max_digits=14)),
                ("discount",models.DecimalField(decimal_places=2,default=0,max_digits=14)),("tax",models.DecimalField(decimal_places=2,default=0,max_digits=14)),
                ("total",models.DecimalField(decimal_places=2,default=0,max_digits=14)),("created_at",models.DateTimeField(auto_now_add=True)),("updated_at",models.DateTimeField(auto_now=True)),
                ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="created_purchase_orders",to=settings.AUTH_USER_MODEL)),
                ("supplier",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="purchase_orders",to="purchase.supplier")),
            ],options={"ordering":["-created_at"],"indexes":[models.Index(fields=["status","order_date"],name="purchase_po_status_1b6c2a_idx"),models.Index(fields=["supplier","status"],name="purchase_po_supplier_4c2c71_idx")]}
        ),
        migrations.CreateModel(
            name="PurchaseItem",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("quantity",models.DecimalField(decimal_places=2,max_digits=12,validators=[django.core.validators.MinValueValidator(0.01)])),
                ("received_quantity",models.DecimalField(decimal_places=2,default=0,max_digits=12,validators=[django.core.validators.MinValueValidator(0)])),
                ("unit_cost",models.DecimalField(decimal_places=2,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
                ("notes",models.TextField(blank=True)),
                ("product",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="purchase_items",to="products.product")),
                ("purchase_order",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="items",to="purchase.purchaseorder")),
            ]
        ),
        migrations.CreateModel(
            name="GoodsReceipt",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("receipt_no",models.CharField(editable=False,max_length=30,unique=True)),("received_date",models.DateField(default=django.utils.timezone.localdate)),
                ("supplier_reference",models.CharField(blank=True,max_length=120)),("notes",models.TextField(blank=True)),("created_at",models.DateTimeField(auto_now_add=True)),
                ("purchase_order",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="receipts",to="purchase.purchaseorder")),
                ("received_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="goods_receipts",to=settings.AUTH_USER_MODEL)),
            ]
        )
    ]
