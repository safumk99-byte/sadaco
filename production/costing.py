from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from products.models import MachineRate, StaffCompensation
from staff.models import StaffProfile

from .models import ProductionCostEntry, ProductionJob, ProductionMaterial


CENT = Decimal("0.01")
RATE_QUANTUM = Decimal("0.000001")


def _quantity(value):
    try:
        quantity = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        raise ValidationError("Enter a valid quantity.")
    if not quantity.is_finite() or quantity <= 0:
        raise ValidationError("Quantity must be a finite number greater than zero.")
    if max(-quantity.as_tuple().exponent, 0) > 3:
        raise ValidationError("Cost quantities support up to 3 decimal places.")
    if quantity > Decimal("99999999999.999"):
        raise ValidationError("Quantity exceeds the supported limit.")
    return quantity


@transaction.atomic
def record_production_cost(*, job_id, cost_type, quantity, user, machine_rate_id=None,
                           staff_id=None, material_line_id=None, description=""):
    job = ProductionJob.objects.select_for_update().select_related(
        "order__customer"
    ).get(pk=job_id)
    quantity = _quantity(quantity)
    department_id = job.order.customer.department_id
    description = str(description or "").strip()[:180]

    if cost_type == ProductionCostEntry.CostType.MACHINE:
        if not machine_rate_id or staff_id:
            raise ValidationError("Select one approved machine/operation rate.")
        rate = MachineRate.objects.select_for_update().filter(
            pk=machine_rate_id, is_active=True
        ).first()
        if not rate:
            raise ValidationError("The selected machine rate is not active or does not exist.")
        if not Decimal(rate.rate).is_finite() or Decimal(rate.rate) <= 0:
            raise ValidationError("The selected machine rate must be a positive verified amount.")

        material_line = None
        if material_line_id:
            material_line = ProductionMaterial.objects.select_for_update(of=("self",)).select_related(
                "material_variant"
            ).filter(pk=material_line_id, job=job).first()
            if not material_line:
                raise ValidationError("The selected material line does not belong to this job.")
            if not material_line.material_variant_id:
                raise ValidationError("Machine cost material matching requires a Material Master line.")

        # Material/thickness-specific rates (the PDF's Multy Wood CNC rates)
        # must match the selected job material exactly. Generic laser rates
        # have blank material and thickness and can be used without a line.
        if rate.material_name or rate.thickness_mm is not None:
            if not material_line or not material_line.material_variant_id:
                raise ValidationError("Select the matching Material Master line for this material-specific rate.")
            variant = material_line.material_variant
            if (
                variant.material_name.casefold() != rate.material_name.casefold()
                or variant.thickness_mm != rate.thickness_mm
            ):
                raise ValidationError("The selected material line does not match this operation rate's material and thickness.")

        if rate.unit not in {"minute", "sqft"}:
            raise ValidationError("This operation rate uses an unsupported unit.")
        unit_rate = Decimal(rate.rate).quantize(RATE_QUANTUM)
        operation_snapshot = rate.operation
        staff = None
        staff_name_snapshot = ""
        unit = rate.unit
        machine_rate = rate
        cost_type = ProductionCostEntry.CostType.MACHINE
        if not description:
            description = rate.get_operation_display()
        material_line_value = material_line

    elif cost_type == ProductionCostEntry.CostType.LABOUR:
        if not staff_id or machine_rate_id or material_line_id:
            raise ValidationError("Select one staff member for a direct-labour entry.")
        staff = StaffProfile.objects.select_for_update().filter(
            pk=staff_id, status=StaffProfile.Status.ACTIVE
        ).first()
        if not staff:
            raise ValidationError("The selected staff member is not active or does not exist.")
        if not department_id or staff.department_id != department_id:
            raise ValidationError("The selected staff member must belong to the job's department.")
        try:
            compensation = StaffCompensation.objects.select_for_update().get(staff=staff, is_active=True)
        except StaffCompensation.DoesNotExist:
            raise ValidationError("No active verified compensation record exists for this staff member.")
        if (
            compensation.payment_type != StaffCompensation.PaymentType.MONTHLY
            or compensation.monthly_salary is None
            or compensation.monthly_salary <= 0
            or compensation.working_days_per_month <= 0
            or compensation.productive_hours_per_day <= 0
        ):
            raise ValidationError("Only monthly-paid staff with a valid salary and productive-hours plan can be costed. Work-based rates are not configured.")
        monthly_hours = Decimal(compensation.working_days_per_month) * compensation.productive_hours_per_day
        unit_rate = (
            compensation.monthly_salary / monthly_hours / Decimal("60")
        ).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
        operation_snapshot = ""
        machine_rate = None
        material_line_value = None
        staff_name_snapshot = str(staff)
        unit = "minute"
        cost_type = ProductionCostEntry.CostType.LABOUR
        if not description:
            description = "Direct labour"

    else:
        raise ValidationError("Cost type must be machine or labour.")

    total_cost = (quantity * unit_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    if total_cost > Decimal("99999999999999.99"):
        raise ValidationError("Calculated production cost exceeds the supported amount.")
    return ProductionCostEntry.objects.create(
        job=job,
        cost_type=cost_type,
        machine_rate=machine_rate,
        staff=staff,
        material_line=material_line_value,
        operation_snapshot=operation_snapshot,
        description=description,
        staff_name_snapshot=staff_name_snapshot,
        quantity=quantity,
        unit=unit,
        unit_rate=unit_rate,
        total_cost=total_cost,
        created_by=user,
    )
