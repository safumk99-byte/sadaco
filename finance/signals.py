from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from sales.models import PaymentRecord
from .models import FinanceTransaction


@receiver(post_save, sender=PaymentRecord)
def sync_customer_payment_to_ledger(sender, instance, created, **kwargs):
    """Keep the finance ledger synchronized with customer payment records."""
    transaction = FinanceTransaction.objects.filter(sales_payment=instance).first()
    if instance.status in (PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED):
        defaults = {
            "transaction_type": FinanceTransaction.Type.INCOME,
            "amount": instance.amount,
            "transaction_date": instance.paid_on or timezone.localdate(),
            "payment_method": instance.payment_method,
            "reference": instance.receipt_no or instance.reference,
            "description": f"{instance.get_payment_type_display()} payment · {instance.order.order_no}",
            "status": FinanceTransaction.Status.POSTED,
            "created_by": instance.created_by,
        }
        if transaction:
            for key, value in defaults.items():
                setattr(transaction, key, value)
            transaction.save(update_fields=list(defaults.keys()))
        else:
            FinanceTransaction.objects.create(sales_payment=instance, **defaults)
    elif transaction and transaction.status != FinanceTransaction.Status.VOID:
        transaction.status = FinanceTransaction.Status.VOID
        transaction.save(update_fields=["status"])
