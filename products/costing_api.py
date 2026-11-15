import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from products.models import MaterialVariant, MachineRate, StaffCompensation
from staff.models import StaffProfile
from accounts.models import UserProfile


def _can_manage_costing(user):
    role = getattr(getattr(user, "profile", None), "role", None)
    return user.is_superuser or role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER)


def _data(request):
    try:
        return json.loads(request.body or "{}")
    except (TypeError, ValueError):
        return {}


def _decimal(value, field, nullable=False):
    if nullable and value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a valid number.")
    if result < 0:
        raise ValueError(f"{field} cannot be negative.")
    return result


def _material_payload(item):
    area = item.sheet_width_ft * item.sheet_height_ft
    sqft_rate = item.purchase_rate / area if item.purchase_rate is not None and area else None
    return {
        "id": item.id, "material_name": item.material_name, "brand": item.brand,
        "thickness_mm": str(item.thickness_mm) if item.thickness_mm is not None else "",
        "variant": item.variant, "colour": item.colour, "colour_label": item.get_colour_display(),
        "sheet_width_ft": str(item.sheet_width_ft), "sheet_height_ft": str(item.sheet_height_ft),
        "sheet_area_sqft": str(area), "purchase_rate": str(item.purchase_rate) if item.purchase_rate is not None else "",
        "retail_rate": str(item.retail_rate) if item.retail_rate is not None else "",
        "purchase_rate_sqft": str(sqft_rate) if sqft_rate is not None else "",
        "supplier_name": item.supplier_name, "stock_quantity": str(item.stock_quantity),
        "unit": item.unit, "is_active": item.is_active,
    }


@require_GET
@login_required
def material_master_api(request):
    if not _can_manage_costing(request.user):
        return JsonResponse({"detail": "You do not have permission to view material rates."}, status=403)
    qs = MaterialVariant.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(material_name__icontains=q) | Q(brand__icontains=q) | Q(variant__icontains=q))
    name = request.GET.get("material", "").strip()
    if name:
        qs = qs.filter(material_name=name)
    return JsonResponse({
        "materials": [_material_payload(x) for x in qs],
        "material_names": list(MaterialVariant.objects.order_by().values_list("material_name", flat=True).distinct()),
        "can_manage": _can_manage_costing(request.user),
    })


@require_POST
@login_required
def material_master_save_api(request, pk=None):
    if not _can_manage_costing(request.user):
        return JsonResponse({"detail": "You do not have permission to edit material rates."}, status=403)
    data = _data(request)
    item = get_object_or_404(MaterialVariant, pk=pk) if pk else MaterialVariant()
    try:
        item.material_name = str(data.get("material_name", item.material_name)).strip()
        if not item.material_name:
            raise ValueError("Material name is required.")
        item.brand = str(data.get("brand", item.brand)).strip()
        item.thickness_mm = _decimal(data.get("thickness_mm", item.thickness_mm), "Thickness", True)
        item.variant = str(data.get("variant", item.variant)).strip()
        item.colour = str(data.get("colour", item.colour or "na"))
        if item.colour not in dict(MaterialVariant.Colour.choices):
            raise ValueError("Invalid colour/variant selection.")
        item.sheet_width_ft = _decimal(data.get("sheet_width_ft", item.sheet_width_ft), "Sheet width")
        item.sheet_height_ft = _decimal(data.get("sheet_height_ft", item.sheet_height_ft), "Sheet height")
        if item.sheet_width_ft <= 0 or item.sheet_height_ft <= 0:
            raise ValueError("Sheet dimensions must be greater than zero.")
        item.purchase_rate = _decimal(data.get("purchase_rate", item.purchase_rate), "Purchase rate", True)
        item.retail_rate = _decimal(data.get("retail_rate", item.retail_rate), "Retail rate", True)
        item.supplier_name = str(data.get("supplier_name", item.supplier_name)).strip()
        item.unit = str(data.get("unit", item.unit or "Sheet")).strip() or "Sheet"
        item.is_active = str(data.get("is_active", item.is_active)).lower() not in ("false", "0", "no")
        item._rate_changed_by = request.user
        item.save()
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    return JsonResponse({"ok": True, "material": _material_payload(item)}, status=201 if not pk else 200)


@require_GET
@login_required
def machine_rates_api(request):
    if not _can_manage_costing(request.user):
        return JsonResponse({"detail": "You do not have permission to view machine rates."}, status=403)
    rates = MachineRate.objects.all()
    return JsonResponse({"rates": [{
        "id": x.id, "operation": x.operation, "operation_label": x.get_operation_display(),
        "material_name": x.material_name, "thickness_mm": str(x.thickness_mm) if x.thickness_mm is not None else "",
        "rate": str(x.rate), "unit": x.unit, "is_active": x.is_active,
    } for x in rates], "can_manage": _can_manage_costing(request.user)})


@require_POST
@login_required
def machine_rate_save_api(request, pk=None):
    if not _can_manage_costing(request.user):
        return JsonResponse({"detail": "You do not have permission to edit machine rates."}, status=403)
    data = _data(request)
    rate = get_object_or_404(MachineRate, pk=pk) if pk else MachineRate()
    try:
        rate.operation = str(data.get("operation", rate.operation)).strip()
        if rate.operation not in dict(MachineRate.Operation.choices):
            raise ValueError("Invalid machine operation.")
        rate.material_name = str(data.get("material_name", rate.material_name)).strip()
        rate.thickness_mm = _decimal(data.get("thickness_mm", rate.thickness_mm), "Thickness", True)
        rate.rate = _decimal(data.get("rate", rate.rate), "Rate")
        rate.unit = str(data.get("unit", rate.unit or "minute")).strip() or "minute"
        rate.is_active = str(data.get("is_active", rate.is_active)).lower() not in ("false", "0", "no")
        rate.save()
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"ok": True, "id": rate.id}, status=201 if not pk else 200)


@require_GET
@login_required
def staff_compensation_api(request):
    if not _can_manage_costing(request.user):
        return JsonResponse({"detail": "You do not have permission to view staff compensation."}, status=403)
    qs = StaffProfile.objects.select_related("user", "compensation").filter(status=StaffProfile.Status.ACTIVE)
    rows = []
    for staff in qs:
        comp = getattr(staff, "compensation", None)
        rows.append({
            "staff_id": staff.id, "name": staff.user.get_full_name() or staff.user.username,
            "staff_code": staff.staff_id,
            "payment_type": comp.payment_type if comp else "",
            "monthly_salary": str(comp.monthly_salary) if comp and comp.monthly_salary is not None else "",
            "hourly_cost": str(comp.hourly_cost) if comp and comp.hourly_cost is not None else "",
            "working_days_per_month": comp.working_days_per_month if comp else 26,
            "productive_hours_per_day": str(comp.productive_hours_per_day) if comp else "8.25",
            "working_hours_month": str(comp.monthly_productive_hours) if comp else "214.5",
        })
    return JsonResponse({"staff": rows, "can_manage": _can_manage_costing(request.user)})


@require_POST
@login_required
def staff_compensation_save_api(request, staff_id):
    if not _can_manage_costing(request.user):
        return JsonResponse({"detail": "You do not have permission to edit staff compensation."}, status=403)
    staff = get_object_or_404(StaffProfile, pk=staff_id)
    data = _data(request)
    payment_type = str(data.get("payment_type", "")).strip()
    if payment_type not in dict(StaffCompensation.PaymentType.choices):
        return JsonResponse({"detail": "Select a valid payment type."}, status=400)
    salary = None
    try:
        if payment_type == StaffCompensation.PaymentType.MONTHLY:
            salary = _decimal(data.get("monthly_salary"), "Monthly salary")
            if salary <= 0:
                raise ValueError("Monthly salary must be greater than zero.")
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    try:
        working_days = int(data.get("working_days_per_month", 26))
        productive_hours = _decimal(data.get("productive_hours_per_day", "8.25"), "Productive hours per day")
        if not 1 <= working_days <= 31 or productive_hours <= 0:
            raise ValueError("Working days must be 1–31 and productive hours must be greater than zero.")
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    comp, _ = StaffCompensation.objects.update_or_create(
        staff=staff,
        defaults={
            "payment_type": payment_type, "monthly_salary": salary, "is_active": True,
            "working_days_per_month": working_days,
            "productive_hours_per_day": productive_hours,
        },
    )
    return JsonResponse({"ok": True, "payment_type": comp.payment_type, "monthly_salary": str(comp.monthly_salary) if comp.monthly_salary is not None else ""})
