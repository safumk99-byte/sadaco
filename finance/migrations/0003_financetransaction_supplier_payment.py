from django.db import migrations, models
import django.db.models.deletion


def link_existing_supplier_payment_transactions(apps, schema_editor):
    SupplierPayment = apps.get_model("finance", "SupplierPayment")
    FinanceTransaction = apps.get_model("finance", "FinanceTransaction")
    for payment in SupplierPayment.objects.all().iterator():
        transaction = FinanceTransaction.objects.filter(
            reference=payment.payment_no,
            sales_payment__isnull=True,
            expense__isnull=True,
            supplier_payment__isnull=True,
        ).order_by("created_at", "pk").first()
        if transaction:
            transaction.supplier_payment_id = payment.pk
            transaction.save(update_fields=["supplier_payment"])


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0002_accounts_control_center"),
    ]

    operations = [
        migrations.AddField(
            model_name="financetransaction",
            name="supplier_payment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="finance_transaction",
                to="finance.supplierpayment",
            ),
        ),
        migrations.RunPython(
            link_existing_supplier_payment_transactions,
            migrations.RunPython.noop,
        ),
    ]
