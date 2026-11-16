from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
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
def issue_material(*, material_id, quantity, user=None, reference="", remarks="", balance_id=None, lot_id=None, employee=None):
    """
    Issue a production material from the department's MaterialStockBalance ledger.
    Legacy Product-based issue remains available only for old lines not yet linked
    to MaterialVariant, so existing historical workflows are not silently broken.
    """
    quantity = Decimal(str(quantity))
    material = ProductionMaterial.objects.select_for_update(of=("self",)).select_related(
        "product", "material_variant", "job", "job__order__customer"
    ).get(pk=material_id)

    if quantity <= 0:
        raise ValidationError("Issue quantity must be greater than zero.")
    pending = material.pending_quantity
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
        if employee and employee.department_id != department_id:
            raise ValidationError("The selected employee does not belong to the job department.")
        if not lot_id:
            raise ValidationError("Select a costed receipt batch before issuing material.")
        from purchase.models import MaterialStockLot
        lot = MaterialStockLot.objects.select_for_update().select_related("balance").filter(
            pk=lot_id, balance_id=balance.pk, balance__material_id=material.material_variant_id,
            balance__department_id=department_id,
        ).first()
        if not lot:
            raise ValidationError("The selected receipt batch does not belong to this material, department and location.")
        if lot.remaining_quantity < quantity:
            raise ValidationError(
                f"Insufficient quantity in selected batch. Available: {lot.remaining_quantity} {material.unit}."
            )
        if balance.quantity < quantity:
            raise ValidationError(f"Insufficient stock at {balance.location}. Available: {balance.quantity} {material.unit}.")
        movement = record_material_movement(
            balance_id=balance.pk, movement_type=MaterialStockMovement.Type.JOB_ISSUE,
            quantity=quantity, user=user, job=material.job, order=material.job.order,
            employee=employee or material.job.assigned_staff, reference=reference or material.job.job_no,
            remarks=remarks or f"Material issued to {material.job.job_no}.",
        )
        lot.remaining_quantity -= quantity
        lot.save(update_fields=["remaining_quantity"])
        material.issued_quantity += quantity
        if material.issue_unit_rate is None:
            material.issue_unit_rate = lot.unit_cost
        material.save(update_fields=["issued_quantity", "issue_unit_rate"])
        issue = MaterialIssue.objects.create(
            job=material.job, material=material, quantity=quantity,
            status=MaterialIssue.Status.ISSUED, reference=reference, remarks=remarks,
            issued_by=user, stock_lot=lot, unit_rate=lot.unit_cost, stock_movement=movement,
        )
        all_ready = all(
            line.pending_quantity <= 0
            for line in material.job.materials.select_related("material_variant").all()
        )
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
    try:
        counted = Decimal(str(counted_quantity))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Counted quantity must be a valid decimal number.")
    if not counted.is_finite():
        raise ValidationError("Counted quantity must be finite.")
    if counted < 0:
        raise ValidationError("Counted quantity cannot be negative.")
    if max(-counted.as_tuple().exponent, 0) > 3:
        raise ValidationError("Counted quantity supports up to three decimal places.")
    if counted > Decimal("99999999999.999"):
        raise ValidationError("Counted quantity exceeds the supported stock quantity.")
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


def _remaining_issue_quantity_after_offcuts(issue, material):
    """Sheet-equivalent quantity still available after offcut area has been separated."""
    remaining = issue.quantity - issue.returned_quantity - issue.wastage_quantity
    if not material.material_variant_id:
        return remaining
    sheet_area = material.material_variant.sheet_area_sqft
    if sheet_area is None or sheet_area <= 0:
        return remaining
    from .models import ReusableOffcut
    registered_area = ReusableOffcut.objects.filter(source_issue=issue).aggregate(
        total=Sum("usable_area_sqft")
    )["total"] or Decimal("0")
    return max(remaining - (registered_area / sheet_area), Decimal("0"))


@transaction.atomic
def return_issued_material(*, material_issue_id, quantity, user=None, reference="", remarks="", employee=None):
    """Return unused material against one exact issue and restore its original receipt lot."""
    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValidationError("Return quantity must be greater than zero.")
    issue = MaterialIssue.objects.select_for_update(of=("self",)).select_related(
        "material", "stock_lot", "stock_movement", "material__job__order__customer"
    ).get(pk=material_issue_id, status=MaterialIssue.Status.ISSUED)
    material = ProductionMaterial.objects.select_for_update(of=("self",)).get(pk=issue.material_id)
    if not material.material_variant_id or not issue.stock_lot_id or issue.unit_rate is None:
        raise ValidationError("Only receipt-batch-tracked issues can be returned through this workflow.")
    available = _remaining_issue_quantity_after_offcuts(issue, material)
    if quantity > available:
        raise ValidationError(
            f"Return exceeds the remaining issue quantity after registered offcuts: {available} {material.unit}."
        )
    lot = issue.stock_lot.__class__.objects.select_for_update().get(pk=issue.stock_lot_id)
    if issue.stock_movement_id and issue.stock_movement.balance_id != lot.balance_id:
        raise ValidationError("The issue receipt batch must match the original issue stock location.")
    balance = MaterialStockBalance.objects.select_for_update().get(
        pk=lot.balance_id, material_id=material.material_variant_id,
        department_id=material.job.order.customer.department_id,
    )
    if employee and employee.department_id != balance.department_id:
        raise ValidationError("The selected employee does not belong to the job department.")
    movement = record_material_movement(
        balance_id=balance.pk, movement_type=MaterialStockMovement.Type.RETURN,
        quantity=quantity, user=user, job=material.job, order=material.job.order,
        employee=employee, reference=reference or material.job.job_no,
        remarks=remarks or f"Unused material returned against issue #{issue.pk}.",
    )
    lot.remaining_quantity += quantity
    lot.save(update_fields=["remaining_quantity"])
    issue.returned_quantity += quantity
    issue.save(update_fields=["returned_quantity"])
    material.returned_quantity += quantity
    material.save(update_fields=["returned_quantity"])
    movement.source_issue = issue
    movement.save(update_fields=["source_issue"])
    return movement


@transaction.atomic
def record_issued_wastage(*, material_issue_id, quantity, user=None, reference="", remarks="", employee=None):
    """Attribute wastage to one issue; stock was deducted when that issue was created."""
    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValidationError("Wastage quantity must be greater than zero.")
    issue = MaterialIssue.objects.select_for_update(of=("self",)).select_related(
        "material", "stock_lot", "stock_movement", "material__job__order__customer"
    ).get(pk=material_issue_id, status=MaterialIssue.Status.ISSUED)
    material = ProductionMaterial.objects.select_for_update(of=("self",)).get(pk=issue.material_id)
    if not material.material_variant_id or not issue.stock_lot_id or issue.unit_rate is None:
        raise ValidationError("Only receipt-batch-tracked issues can record wastage through this workflow.")
    available = _remaining_issue_quantity_after_offcuts(issue, material)
    if quantity > available:
        raise ValidationError(
            f"Wastage exceeds the remaining issue quantity after registered offcuts: {available} {material.unit}."
        )
    lot = issue.stock_lot.__class__.objects.select_for_update().get(pk=issue.stock_lot_id)
    if issue.stock_movement_id and issue.stock_movement.balance_id != lot.balance_id:
        raise ValidationError("The issue receipt batch must match the original issue stock location.")
    balance = MaterialStockBalance.objects.select_for_update().get(
        pk=lot.balance_id, material_id=material.material_variant_id,
        department_id=material.job.order.customer.department_id,
    )
    if employee and employee.department_id != balance.department_id:
        raise ValidationError("The selected employee does not belong to the job department.")
    movement = MaterialStockMovement.objects.create(
        balance=balance, source_issue=issue, movement_type=MaterialStockMovement.Type.WASTAGE,
        quantity=quantity, balance_after=balance.quantity, job=material.job,
        order=material.job.order, employee=employee, reference=reference or material.job.job_no,
        remarks=remarks or f"Wastage recorded against issue #{issue.pk}; stock was already deducted.",
        created_by=user,
    )
    issue.wastage_quantity += quantity
    issue.save(update_fields=["wastage_quantity"])
    material.wastage_quantity += quantity
    material.save(update_fields=["wastage_quantity"])
    return movement


def reconcile_material_stock_balance(balance):
    """Read-only reconciliation of the stock movement ledger and receipt lots.

    Wastage rows annotate material already deducted at issue time, so they do
    not create a second stock decrement. Offcut area is tracked separately
    and never changes sheet-unit stock.
    """
    from .models import MaterialStockMovement

    positive = {
        MaterialStockMovement.Type.OPENING,
        MaterialStockMovement.Type.PURCHASE_RECEIPT,
        MaterialStockMovement.Type.RETURN,
        MaterialStockMovement.Type.OFFCUT_IN,
    }
    negative = {MaterialStockMovement.Type.JOB_ISSUE}
    # The API prefetches movements in chronological order for all visible balances.
    movements = list(balance.movements.all())
    movement_expected = Decimal("0")
    unknown_types = []
    # Keep the calculation deterministic even when the caller did not prefetch
    # movements in chronological order. Correction/closing rows are balance
    # snapshots, not additive quantities: reset the running ledger to the
    # recorded post-count balance.
    movements.sort(key=lambda row: (row.created_at, row.pk))
    for movement in movements:
        if movement.movement_type in positive:
            movement_expected += movement.quantity
        elif movement.movement_type in negative:
            movement_expected -= movement.quantity
        elif movement.movement_type in (
            MaterialStockMovement.Type.CORRECTION,
            MaterialStockMovement.Type.CLOSING,
        ):
            movement_expected = movement.balance_after
        elif movement.movement_type != MaterialStockMovement.Type.WASTAGE:
            unknown_types.append(movement.movement_type)

    # Receipt lots and their issue history are prefetched by the API caller.
    lots = list(balance.cost_lots.all())
    lot_remaining_total = Decimal("0")
    lot_mismatches = []
    for lot in lots:
        issued = sum((issue.quantity for issue in lot.issues.all()), Decimal("0"))
        returned = sum((issue.returned_quantity for issue in lot.issues.all()), Decimal("0"))
        expected_remaining = lot.original_quantity - issued + returned
        lot_remaining_total += lot.remaining_quantity
        if expected_remaining != lot.remaining_quantity:
            lot_mismatches.append({
                "lot_id": lot.pk,
                "expected_remaining": str(expected_remaining),
                "recorded_remaining": str(lot.remaining_quantity),
            })

    movement_difference = balance.quantity - movement_expected
    unbatched_quantity = balance.quantity - lot_remaining_total
    return {
        "balance_id": balance.pk,
        "material_id": balance.material_id,
        "material": str(balance.material),
        "department_id": balance.department_id,
        "department": balance.department.name,
        "location": balance.location,
        "recorded_balance": str(balance.quantity),
        "movement_expected_balance": str(movement_expected),
        "movement_difference": str(movement_difference),
        "receipt_lot_remaining": str(lot_remaining_total),
        "unbatched_quantity": str(unbatched_quantity),
        "lot_count": len(lots),
        "lot_mismatches": lot_mismatches,
        "unknown_movement_types": sorted(set(unknown_types)),
        "reconciled": (
            movement_difference == 0 and not lot_mismatches and not unknown_types
        ),
        "unbatched_warning": unbatched_quantity != 0,
    }


@transaction.atomic
def submit_material_stock_count(*, balance_id, counted_quantity, user=None, reason=""):
    from .models import MaterialStockCount
    counted = Decimal(str(counted_quantity))
    if counted < 0:
        raise ValidationError("Counted quantity cannot be negative.")
    balance = MaterialStockBalance.objects.select_for_update().get(pk=balance_id)
    variance = counted - balance.quantity
    return MaterialStockCount.objects.create(
        balance=balance, system_quantity=balance.quantity, counted_quantity=counted,
        variance=variance, reason=reason.strip(), submitted_by=user,
    )


@transaction.atomic
def review_material_stock_count(*, count_id, approve, user=None, review_note=""):
    from .models import MaterialStockCount
    count = MaterialStockCount.objects.select_for_update().select_related("balance").get(pk=count_id)
    if count.status != MaterialStockCount.Status.PENDING:
        raise ValidationError("This physical count has already been reviewed.")
    balance = MaterialStockBalance.objects.select_for_update().get(pk=count.balance_id)
    if approve:
        if balance.quantity != count.system_quantity:
            raise ValidationError(
                "Stock changed after this count was submitted. Submit a fresh physical count before approval."
            )
        if count.variance:
            balance.quantity = count.counted_quantity
            balance.save(update_fields=["quantity", "updated_at"])
            movement = MaterialStockMovement.objects.create(
                balance=balance, movement_type=MaterialStockMovement.Type.CORRECTION,
                quantity=abs(count.variance), balance_after=count.counted_quantity,
                reference=f"PHYSICAL-COUNT-{count.pk}",
                remarks=(count.reason + " " + review_note).strip() or "Approved physical stock count variance.",
                created_by=user,
            )
            count.correction_movement = movement
        count.status = MaterialStockCount.Status.APPROVED
    else:
        count.status = MaterialStockCount.Status.REJECTED
    count.reviewed_by = user
    count.reviewed_at = timezone.now()
    count.save(update_fields=["status", "reviewed_by", "reviewed_at", "correction_movement"])
    return count
