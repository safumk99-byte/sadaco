import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserProfile
from core.models import Department
from products.models import MaterialVariant
from staff.models import StaffProfile
from production.models import ProductionJob
from .models import MaterialStockBalance, MaterialStockMovement, ReusableOffcut
from .services import record_material_movement


def _manager_department(user):
    profile = getattr(user, "profile", None)
    if user.is_superuser or (profile and profile.role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)):
        return None
    if profile and profile.role == UserProfile.Role.MANAGER:
        return profile.department_id
    return False


def _visible_balances(user):
    scope = _manager_department(user)
    qs = MaterialStockBalance.objects.select_related("material", "department")
    if scope is None:
        return qs
    if scope is False or not scope:
        return qs.none()
    return qs.filter(department_id=scope)


@require_GET
@login_required
def material_stock_api(request):
    qs = _visible_balances(request.user)
    q = request.GET.get("q", "").strip()
    department = request.GET.get("department", "").strip()
    if q:
        qs = qs.filter(Q(material__material_name__icontains=q) | Q(material__brand__icontains=q) | Q(material__variant__icontains=q) | Q(location__icontains=q))
    if department and _manager_department(request.user) is None:
        qs = qs.filter(department_id=department)
    rows = [{
        "id": x.id, "material_id": x.material_id, "material": x.material.material_name,
        "brand": x.material.brand, "thickness_mm": str(x.material.thickness_mm) if x.material.thickness_mm is not None else None,
        "variant": x.material.variant, "colour": x.material.get_colour_display(), "unit": x.material.unit,
        "sheet_width_ft": str(x.material.sheet_width_ft), "sheet_height_ft": str(x.material.sheet_height_ft),
        "department_id": x.department_id, "department": x.department.name, "location": x.location,
        "quantity": str(x.quantity), "minimum_quantity": str(x.minimum_quantity) if x.minimum_quantity is not None else None,
        "is_low_stock": x.minimum_quantity is not None and x.quantity <= x.minimum_quantity,
        "purchase_rate": str(x.material.purchase_rate) if x.material.purchase_rate is not None else None,
        "supplier": x.material.supplier_name,
    } for x in qs]
    totals = qs.aggregate(total=Sum("quantity"))
    return JsonResponse({"items": rows, "total_quantity": str(totals["total"] or Decimal("0")), "can_manage": _manager_department(request.user) is None})


@require_GET
@login_required
def material_movements_api(request):
    qs = MaterialStockMovement.objects.select_related("balance__material", "balance__department", "job", "order", "employee", "created_by")
    scope = _manager_department(request.user)
    if scope is not None:
        qs = qs.filter(balance__department_id=scope) if scope else qs.none()
    material = request.GET.get("material", "").strip()
    if material:
        qs = qs.filter(balance__material_id=material)
    return JsonResponse({"items": [{
        "id": x.id, "material": x.balance.material.material_name, "brand": x.balance.material.brand,
        "department": x.balance.department.name, "location": x.balance.location,
        "type": x.movement_type, "type_label": x.get_movement_type_display(),
        "quantity": str(x.quantity), "balance_after": str(x.balance_after),
        "job": x.job.job_no if x.job_id else None, "order": x.order.order_no if x.order_id else None,
        "employee": x.employee.user.get_full_name() if x.employee_id and x.employee.user_id else None,
        "reference": x.reference, "remarks": x.remarks, "created_by": x.created_by.get_full_name() if x.created_by else None,
        "created_at": x.created_at.isoformat(),
    } for x in qs[:500]]})


@require_POST
@login_required
def material_movement_create_api(request):
    try:
        data = json.loads(request.body or "{}")
        balance = _visible_balances(request.user).get(pk=data.get("balance"))
        scope = _manager_department(request.user)
        if scope is False:
            return JsonResponse({"detail": "You do not have permission to manage material stock."}, status=403)
        job = ProductionJob.objects.filter(pk=data.get("job")).select_related("order__customer").first() if data.get("job") else None
        if data.get("job") and not job:
            return JsonResponse({"detail": "Production job not found."}, status=404)
        employee = StaffProfile.objects.filter(pk=data.get("employee")).first() if data.get("employee") else None
        movement = record_material_movement(
            balance_id=balance.pk, movement_type=data.get("type"), quantity=data.get("quantity"),
            user=request.user, job=job, employee=employee, reference=str(data.get("reference", "")),
            remarks=str(data.get("remarks", "")),
        )
        return JsonResponse({"ok": True, "movement_id": movement.pk, "balance_after": str(movement.balance_after)}, status=201)
    except (ValueError, TypeError, InvalidOperation, MaterialStockBalance.DoesNotExist, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_GET
@login_required
def material_options_api(request):
    scope = _manager_department(request.user)
    materials = MaterialVariant.objects.filter(is_active=True).order_by("material_name", "brand", "thickness_mm")
    departments = Department.objects.filter(is_active=True)
    if scope is not None:
        if not scope:
            return JsonResponse({"materials": [], "departments": [], "locations": []})
        departments = departments.filter(pk=scope)
    return JsonResponse({
        "materials": [{"id": x.id, "name": x.material_name, "brand": x.brand, "thickness_mm": str(x.thickness_mm) if x.thickness_mm is not None else None, "variant": x.variant, "colour": x.get_colour_display(), "unit": x.unit} for x in materials],
        "departments": [{"id": x.id, "name": x.name, "code": x.code} for x in departments],
        "locations": [],
    })


@require_POST
@login_required
def material_balance_create_api(request):
    if _manager_department(request.user) is not None:
        return JsonResponse({"detail": "Only Founder/Admin can create stock balances and assign departments."}, status=403)
    try:
        data = json.loads(request.body or "{}")
        department = Department.objects.get(pk=data.get("department"), is_active=True)
        material = MaterialVariant.objects.get(pk=data.get("material"), is_active=True)
        location = str(data.get("location", "")).strip()
        if not location:
            return JsonResponse({"detail": "Location is required."}, status=400)
        balance, created = MaterialStockBalance.objects.get_or_create(
            material=material, department=department, location=location,
            defaults={"quantity": Decimal("0"), "minimum_quantity": data.get("minimum_quantity") or None},
        )
        if not created:
            return JsonResponse({"detail": "A balance for this material, department and location already exists."}, status=400)
        return JsonResponse({"ok": True, "id": balance.pk}, status=201)
    except (ValueError, TypeError, InvalidOperation, Department.DoesNotExist, MaterialVariant.DoesNotExist) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_GET
@login_required
def offcuts_api(request):
    qs = ReusableOffcut.objects.select_related("material", "department", "source_job", "used_for_job")
    scope = _manager_department(request.user)
    if scope is not None:
        qs = qs.filter(department_id=scope) if scope else qs.none()
    return JsonResponse({"items": [{
        "id": x.id, "material": x.material.material_name, "brand": x.material.brand,
        "department": x.department.name, "location": x.location, "thickness_mm": str(x.thickness_mm) if x.thickness_mm is not None else None,
        "length_mm": str(x.length_mm), "width_mm": str(x.width_mm), "usable_area_sqft": str(x.usable_area_sqft),
        "status": x.status, "source_job": x.source_job.job_no if x.source_job_id else None,
        "used_for_job": x.used_for_job.job_no if x.used_for_job_id else None, "notes": x.notes,
    } for x in qs[:500]]})
