from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Product, StockTransaction


@transaction.atomic
def record_stock_transaction(
    *,
    product_id,
    transaction_type,
    quantity,
    user=None,
    reference="",
    remarks="",
):
    quantity = Decimal(str(quantity))
    if quantity < 0:
        raise ValidationError("Quantity cannot be negative.")

    product = Product.objects.select_for_update().get(pk=product_id)
    current = product.stock_quantity

    if transaction_type == StockTransaction.TransactionType.IN:
        new_balance = current + quantity
    elif transaction_type == StockTransaction.TransactionType.OUT:
        new_balance = current - quantity
        if new_balance < 0:
            raise ValidationError(
                f"Insufficient stock. Available quantity: {current} {product.unit}."
            )
    elif transaction_type == StockTransaction.TransactionType.ADJUSTMENT:
        new_balance = quantity
    else:
        raise ValidationError("Invalid stock transaction type.")

    product.stock_quantity = new_balance
    product.save(update_fields=["stock_quantity", "updated_at"])

    return StockTransaction.objects.create(
        product=product,
        transaction_type=transaction_type,
        quantity=quantity,
        balance_after=new_balance,
        reference=reference.strip(),
        remarks=remarks.strip(),
        created_by=user,
    )


def stock_summary():
    from django.db.models import F, Sum
    from .models import Product

    return {
        "total_units": Product.objects.aggregate(total=Sum("stock_quantity"))["total"] or Decimal("0"),
        "low_stock_products": Product.objects.filter(
            status=Product.Status.ACTIVE,
            stock_quantity__lte=F("low_stock_threshold"),
        ).count(),
        "out_of_stock": Product.objects.filter(
            status=Product.Status.ACTIVE,
            stock_quantity=0,
        ).count(),
    }
