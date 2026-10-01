from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from products.inventory import record_stock_transaction
from production.models import ProductionMaterial
from .models import MaterialIssue, StockCount, ReorderAlert


@transaction.atomic
def issue_material(*, material_id, quantity, user=None, reference="", remarks=""):
    quantity = Decimal(str(quantity))
    material = ProductionMaterial.objects.select_for_update().select_related("product", "job").get(pk=material_id)

    if not material.product_id:
        raise ValidationError("This production material is not linked to a stock product.")
    if quantity <= 0:
        raise ValidationError("Issue quantity must be greater than zero.")

    pending = material.quantity_required - material.issued_quantity
    if quantity > pending:
        raise ValidationError(f"Cannot issue more than pending requirement: {pending} {material.unit}.")

    product = material.product.__class__.objects.select_for_update().get(pk=material.product_id)
    if product.stock_quantity < quantity:
        raise ValidationError(
            f"Insufficient stock. Available: {product.stock_quantity} {product.unit}."
        )

    record = record_stock_transaction(
        product_id=product.pk,
        transaction_type="out",
        quantity=quantity,
        user=user,
        reference=reference or material.job.job_no,
        remarks=remarks or f"Material issued to {material.job.job_no}.",
    )

    material.issued_quantity += quantity
    material.save(update_fields=["issued_quantity"])

    issue = MaterialIssue.objects.create(
        job=material.job,
        material=material,
        quantity=quantity,
        status=MaterialIssue.Status.ISSUED,
        reference=reference,
        remarks=remarks,
        issued_by=user,
    )

    job = material.job
    all_ready = not job.materials.filter(issued_quantity__lt=F("quantity_required")).exists()
    if all_ready and not job.material_ready:
        job.material_ready = True
        job.save(update_fields=["material_ready", "updated_at"])

    return issue, record


@transaction.atomic
def complete_stock_count(*, product_id, counted_quantity, user=None, reason=""):
    from products.models import Product
    product = Product.objects.select_for_update().get(pk=product_id)
    counted = Decimal(str(counted_quantity))
    if counted < 0:
        raise ValidationError("Counted quantity cannot be negative.")

    system = product.stock_quantity
    variance = counted - system
    StockCount.objects.create(
        product=product,
        system_quantity=system,
        counted_quantity=counted,
        variance=variance,
        reason=reason,
        counted_by=user,
    )
    if variance != 0:
        record_stock_transaction(
            product_id=product.pk,
            transaction_type="adjustment",
            quantity=counted,
            user=user,
            reference="STOCK-COUNT",
            remarks=reason or f"Physical count variance: {variance}.",
        )
    return variance


def sync_reorder_alerts():
    from products.models import Product
    active = Product.objects.filter(status=Product.Status.ACTIVE)
    alerts = []
    for product in active:
        alert, _ = ReorderAlert.objects.get_or_create(product=product)
        if product.stock_quantity <= product.low_stock_threshold:
            if not alert.is_open:
                alert.is_open = True
                alert.save(update_fields=["is_open", "updated_at"])
            alerts.append(alert)
        elif alert.is_open:
            alert.is_open = False
            alert.save(update_fields=["is_open", "updated_at"])
    return alerts
