from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial=True
    dependencies=[("sales","0004_link_requests_to_quotations"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(
            name="ExpenseCategory",
            fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("name",models.CharField(max_length=120,unique=True)),("is_active",models.BooleanField(default=True))]
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("expense_no",models.CharField(editable=False,max_length=30,unique=True)),("amount",models.DecimalField(decimal_places=2,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
                ("expense_date",models.DateField(default=django.utils.timezone.localdate)),("payment_method",models.CharField(default="cash",max_length=30)),
                ("reference",models.CharField(blank=True,max_length=120)),("description",models.TextField(blank=True)),
                ("status",models.CharField(choices=[("draft","Draft"),("paid","Paid"),("cancelled","Cancelled")],default="paid",max_length=20)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("category",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="expenses",to="finance.expensecategory")),
                ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="created_expenses",to=settings.AUTH_USER_MODEL)),
            ],options={"ordering":["-expense_date","-created_at"],"indexes":[models.Index(fields=["status","expense_date"],name="finance_exp_status_6b5a11_idx"),models.Index(fields=["category","expense_date"],name="finance_exp_category_9f7b10_idx")]}
        ),
        migrations.CreateModel(
            name="FinanceTransaction",
            fields=[
                ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
                ("transaction_no",models.CharField(editable=False,max_length=30,unique=True)),("transaction_type",models.CharField(choices=[("income","Income"),("expense","Expense")],max_length=20)),
                ("amount",models.DecimalField(decimal_places=2,max_digits=14,validators=[django.core.validators.MinValueValidator(0)])),
                ("transaction_date",models.DateField(default=django.utils.timezone.localdate)),("payment_method",models.CharField(default="cash",max_length=30)),
                ("reference",models.CharField(blank=True,max_length=120)),("description",models.TextField(blank=True)),
                ("status",models.CharField(choices=[("posted","Posted"),("void","Void")],default="posted",max_length=20)),("created_at",models.DateTimeField(auto_now_add=True)),
                ("created_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="finance_transactions",to=settings.AUTH_USER_MODEL)),
                ("expense",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="finance_transactions",to="finance.expense")),
                ("sales_payment",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="finance_transactions",to="sales.paymentrecord")),
            ],options={"ordering":["-transaction_date","-created_at"],"indexes":[models.Index(fields=["transaction_type","transaction_date"],name="finance_txn_type_5a8c4d_idx"),models.Index(fields=["status","transaction_date"],name="finance_txn_status_7e6b2c_idx")]}
        )
    ]
