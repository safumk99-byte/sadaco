from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.core.validators import MinValueValidator
from django.utils import timezone


def backfill_payment_transactions(apps, schema_editor):
    PaymentRecord = apps.get_model("sales", "PaymentRecord")
    FinanceTransaction = apps.get_model("finance", "FinanceTransaction")
    for payment in PaymentRecord.objects.filter(status__in=["received", "verified"]):
        FinanceTransaction.objects.get_or_create(
            sales_payment_id=payment.pk,
            defaults={
                "transaction_no": f"TXN-{uuid.uuid4().hex[:10].upper()}",
                "transaction_type": "income",
                "amount": payment.amount,
                "transaction_date": payment.paid_on or timezone.localdate(),
                "payment_method": getattr(payment, "payment_method", "cash"),
                "reference": payment.receipt_no or payment.reference or "",
                "description": f"Customer payment · {payment.order_id}",
                "status": "posted",
                "created_by_id": payment.created_by_id,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0001_initial"),
        ("sales", "0006_paymentrecord_accounts_fields"),
        ("purchase", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="SupplierPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_no", models.CharField(editable=False, max_length=30, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[MinValueValidator(0)])),
                ("payment_date", models.DateField(default=timezone.localdate)),
                ("payment_method", models.CharField(default="cash", max_length=20)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("cancelled", "Cancelled")], default="paid", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_supplier_payments", to=settings.AUTH_USER_MODEL)),
                ("purchase_order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_payments", to="purchase.purchaseorder")),
            ],
            options={
                "ordering": ["-payment_date", "-created_at"],
                "indexes": [
                    models.Index(fields=["purchase_order", "status"], name="finance_sup_purchase_4f3b1a_idx"),
                    models.Index(fields=["payment_date", "status"], name="finance_sup_payment_8d7e1f_idx"),
                ],
            },
        ),
        migrations.RunPython(backfill_payment_transactions, migrations.RunPython.noop),
    ]
