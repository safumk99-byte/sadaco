from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from products.inventory import record_stock_transaction
from production.models import ProductionMaterial
from .models import MaterialIssue, StockCount, ReorderAlert, MaterialStockBalance, MaterialStockMovement


@transaction.atomic
def record_material_movement(*, balance_id, movement_type, quantity, user=None, job=None, order=None, employee=None, reference="", remarks=""):
    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValidationError("Movement quantity must be greater than zero.")
    balance = MaterialStockBalance.objects.select_for_update().select_related("department", "material").get(pk=balance_id)
    incoming = {MaterialStockMovement.Type.OPENING, MaterialStockMovement.Type.PURCHASE_RECEIPT, MaterialStockMovement.Type.RETURN, MaterialStockMovement.Type.OFFCUT_IN}
    outgoing = {MaterialStockMovement.Type.JOB_ISSUE, MaterialStockMovement.Type.WASTAGE}
    if movement_type in incoming:
        new_balance = balance.quantity + quantity
    elif movement_type in outgoing:
        new_balance = balance.quantity - quantity
        if new_balance < 0:
            raise ValidationError(f"Insufficient stock. Available: {balance.quantity} {balance.material.unit}.")
    elif movement_type in (MaterialStockMovement.Type.CLOSING, MaterialStockMovement.Type.CORRECTION):
        raise ValidationError("Closing and correction movements require a reviewed physical-count workflow.")
    else:
        raise ValidationError("Invalid material movement type.")
    if movement_type == MaterialStockMovement.Type.JOB_ISSUE and not job:
        raise ValidationError("A production job is required for job issue.")
    if job and job.order_id:
        order = order or job.order
        if order.customer.department_id != balance.department_id:
            raise ValidationError("The job/order and stock department do not match.")
    balance.quantity = new_balance
    balance.save(update_fields=["quantity", "updated_at"])
    return MaterialStockMovement.objects.create(
        balance=balance, movement_type=movement_type, quantity=quantity, balance_after=new_balance,
        job=job, order=order, employee=employee, reference=reference.strip(), remarks=remarks.strip(), created_by=user,
    )


@transaction.atomic
def issue_material(*, material_id, quantity, user=None, reference="", remarks="", balance_id=None, employee=None):
    """
    Issue a production material from the department's MaterialStockBalance ledger.
    Legacy Product-based issue remains available only for old lines not yet linked
    to MaterialVariant, so existing historical workflows are not silently broken.
    """
    quantity = Decimal(str(quantity))
    material = ProductionMaterial.objects.select_for_update().select_related(
        "product", "material_variant", "job", "job__order__customer"
    ).get(pk=material_id)

    if quantity <= 0:
        raise ValidationError("Issue quantity must be greater than zero.")
    pending = material.quantity_required - material.issued_quantity
    if quantity > pending:
        raise ValidationError(f"Cannot issue more than pending requirement: {pending} {material.unit}.")

    if material.material_variant_id:
        from .models import MaterialStockBalance
        department_id = material.job.order.customer.department_id
        if not department_id:
            raise ValidationError("The order customer must be assigned to a department before issuing material.")
        balances = MaterialStockBalance.objects.filter(
            material_id=material.material_variant_id,
            department_id=department_id,
        )
        if balance_id:
            balances = balances.filter(pk=balance_id)
        matching = list(balances.order_by("location")[:2])
        if not matching:
            raise ValidationError("No stock balance exists for this material in the job department.")
        if len(matching) > 1 and not balance_id:
            raise ValidationError("Select the stock location for this material issue.")
        balance = matching[0]
        if balance.quantity < quantity:
            raise ValidationError(f"Insufficient stock at {balance.location}. Available: {balance.quantity} {material.unit}.")
        if employee and employee.department_id != department_id:
            raise ValidationError("The selected employee does not belong to the job department.")
        unit_rate = material.material_variant.purchase_rate
        if unit_rate is None:
            raise ValidationError("A purchase rate must be recorded before this material can be issued for job costing.")
        movement = record_material_movement(
            balance_id=balance.pk,
            movement_type=MaterialStockMovement.Type.JOB_ISSUE,
            quantity=quantity,
            user=user,
            job=material.job,
            order=material.job.order,
            employee=employee or material.job.assigned_staff,
            reference=reference or material.job.job_no,
            remarks=remarks or f"Material issued to {material.job.job_no}.",
        )
        material.issued_quantity += quantity
        if material.issue_unit_rate is None:
            material.issue_unit_rate = unit_rate
        material.save(update_fields=["issued_quantity", "issue_unit_rate"])
        issue = MaterialIssue.objects.create(
            job=material.job, material=material, quantity=quantity,
            status=MaterialIssue.Status.ISSUED, reference=reference,
            remarks=remarks, issued_by=user,
        )
        all_ready = not material.job.materials.filter(issued_quantity__lt=F("quantity_required")).exists()
        if all_ready and not material.job.material_ready:
            material.job.material_ready = True
            material.job.save(update_fields=["material_ready", "updated_at"])
        return issue, movement

    # Backward compatibility for legacy ProductionMaterial rows still linked to Product.
    if not material.product_id:
        raise ValidationError("Link this production material to the Material Master before issuing stock.")
    product = material.product.__class__.objects.select_for_update().get(pk=material.product_id)
    if product.stock_quantity < quantity:
        raise ValidationError(f"Insufficient stock. Available: {product.stock_quantity} {product.unit}.")
    record = record_stock_transaction(
        product_id=product.pk, transaction_type="out", quantity=quantity, user=user,
        reference=reference or material.job.job_no,
        remarks=remarks or f"Material issued to {material.job.job_no}.",
    )
    material.issued_quantity += quantity
    material.save(update_fields=["issued_quantity"])
    issue = MaterialIssue.objects.create(
        job=material.job, material=material, quantity=quantity,
        status=MaterialIssue.Status.ISSUED, reference=reference,
        remarks=remarks, issued_by=user,
    )
    all_ready = not material.job.materials.filter(issued_quantity__lt=F("quantity_required")).exists()
    if all_ready and not material.job.material_ready:
        material.job.material_ready = True
        material.job.save(update_fields=["material_ready", "updated_at"])
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
    StockCount.objects.create(product=product, system_quantity=system, counted_quantity=counted, variance=variance, reason=reason, counted_by=user)
    if variance != 0:
        record_stock_transaction(product_id=product.pk, transaction_type="adjustment", quantity=counted, user=user, reference="STOCK-COUNT", remarks=reason or f"Physical count variance: {variance}.")
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
