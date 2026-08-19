from django.db import migrations, models
import django.db.models.deletion


def fill_receipts(apps, schema_editor):
    PaymentRecord = apps.get_model("sales", "PaymentRecord")
    import uuid
    for payment in PaymentRecord.objects.filter(receipt_no__isnull=True):
        payment.receipt_no = f"REC-{uuid.uuid4().hex[:10].upper()}"
        payment.save(update_fields=["receipt_no"])


class Migration(migrations.Migration):
    dependencies = [("sales", "0005_customerinteraction")]
    operations = [
        migrations.AddField(
            model_name="paymentrecord",
            name="payment_method",
            field=models.CharField(default="cash", max_length=20),
        ),
        migrations.AddField(
            model_name="paymentrecord",
            name="receipt_no",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.RunPython(fill_receipts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="paymentrecord",
            name="receipt_no",
            field=models.CharField(blank=True, editable=False, max_length=30, unique=True),
        ),
    ]
