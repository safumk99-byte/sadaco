import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserProfile
from core.models import Department
from products.models import MaterialVariant
from staff.models import StaffProfile
from production.models import ProductionJob
from .models import MaterialStockBalance, MaterialStockMovement, MaterialStockCount, ReusableOffcut, MaterialIssue, OffcutUsage
from purchase.models import MaterialStockLot
from .services import record_material_movement


def _manager_department(user):
    profile = getattr(user, "profile", None)
    if user.is_superuser or (profile and profile.is_active and profile.role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)):
        return None
    if profile and profile.is_active and profile.role == UserProfile.Role.MANAGER:
        return profile.department_id or False
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
def material_stock_lots_api(request):
    qs = MaterialStockLot.objects.select_related("balance", "receipt_line__receipt", "receipt_line__purchase_item__purchase_order")
    scope = _manager_department(request.user)
    if scope is not None:
        qs = qs.filter(balance__department_id=scope) if scope else qs.none()
    balance_id = request.GET.get("balance", "").strip()
    if balance_id:
        qs = qs.filter(balance_id=balance_id)
    return JsonResponse({"items": [{
        "id": lot.pk, "balance_id": lot.balance_id,
        "receipt_no": lot.receipt_line.receipt.receipt_no,
        "received_date": lot.receipt_line.receipt.received_date.isoformat(),
        "purchase_order": lot.receipt_line.receipt.purchase_order.po_no,
        "original_quantity": str(lot.original_quantity),
        "remaining_quantity": str(lot.remaining_quantity),
        "unit_cost": str(lot.unit_cost),
    } for lot in qs.filter(remaining_quantity__gt=0)[:500]]})


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
        movement_type = data.get("type")
        if movement_type != MaterialStockMovement.Type.OPENING:
            return JsonResponse({"detail": "Use the dedicated purchase receipt, job issue, return, wastage, or offcut workflow. Direct movement entry is disabled for this movement type."}, status=400)
        if scope is not None:
            return JsonResponse({"detail": "Only Founder/Admin can record opening stock."}, status=403)
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
    scope = _manager_department(request.user)
    if scope is False:
        return JsonResponse({"detail": "You do not have permission to create stock balances."}, status=403)
    try:
        data = json.loads(request.body or "{}")
        department_id = scope if scope is not None else data.get("department")
        department = Department.objects.get(pk=department_id, is_active=True)
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
    qs = ReusableOffcut.objects.select_related(
        "material", "department", "source_job", "used_for_job", "source_issue",
        "source_lot__receipt_line__receipt",
    ).prefetch_related("usages")
    scope = _manager_department(request.user)
    if scope is not None:
        qs = qs.filter(department_id=scope) if scope else qs.none()
    items = []
    for x in qs[:500]:
        used_area = sum((u.used_area_sqft for u in x.usages.all()), Decimal("0"))
        items.append({
            "id": x.id, "material": x.material.material_name, "brand": x.material.brand,
            "material_id": x.material_id, "department": x.department.name, "department_id": x.department_id,
            "location": x.location, "thickness_mm": str(x.thickness_mm) if x.thickness_mm is not None else None,
            "length_mm": str(x.length_mm), "width_mm": str(x.width_mm),
            "usable_area_sqft": str(x.usable_area_sqft), "used_area_sqft": str(used_area),
            "remaining_area_sqft": str(max(x.usable_area_sqft - used_area, Decimal("0"))),
            "cost_per_sqft": str(x.cost_per_sqft) if x.cost_per_sqft is not None else None,
            "source_issue_id": x.source_issue_id,
            "source_receipt": x.source_lot.receipt_line.receipt.receipt_no if x.source_lot_id else None,
            "status": x.status, "source_job": x.source_job.job_no if x.source_job_id else None,
            "used_for_job": x.used_for_job.job_no if x.used_for_job_id else None, "notes": x.notes,
        })
    return JsonResponse({"items": items})


@require_POST
@login_required
def offcut_create_api(request):
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        if scope is False:
            return JsonResponse({"detail": "You do not have permission to manage offcuts."}, status=403)
        department_id = scope if scope is not None else data.get("department")
        department = Department.objects.get(pk=department_id, is_active=True)
        material = MaterialVariant.objects.get(pk=data.get("material"), is_active=True)
        location = str(data.get("location", "")).strip()
        if not location:
            return JsonResponse({"detail": "Location is required."}, status=400)
        if material.unit.strip().lower() not in {"sheet", "sheets"}:
            return JsonResponse({"detail": "Area-based offcuts can only be registered against sheet-based materials."}, status=400)
        length_mm = Decimal(str(data.get("length_mm")))
        width_mm = Decimal(str(data.get("width_mm")))
        usable_area = Decimal(str(data.get("usable_area_sqft")))
        if length_mm <= 0 or width_mm <= 0 or usable_area <= 0:
            return JsonResponse({"detail": "Dimensions and usable area must be greater than zero."}, status=400)
        gross_area_sqft = (length_mm * width_mm) / Decimal("92903.04")
        if usable_area > gross_area_sqft:
            return JsonResponse({"detail": f"Usable area cannot exceed the measured rectangle area ({gross_area_sqft.quantize(Decimal('0.0001'))} sq ft)."}, status=400)
        issue = MaterialIssue.objects.select_for_update().select_related(
            "job__order__customer", "material__material_variant", "stock_lot__balance"
        ).get(pk=data.get("source_issue"), status=MaterialIssue.Status.ISSUED)
        if issue.material.material_variant_id != material.pk or not issue.stock_lot_id:
            return JsonResponse({"detail": "The source issue must belong to this material and have a receipt-costed stock batch."}, status=400)
        if issue.stock_lot.balance.material_id != material.pk or issue.stock_lot.balance.department_id != department.pk:
            return JsonResponse({"detail": "The source receipt batch must belong to this material and department."}, status=400)
        if issue.job.order.customer.department_id != department.pk:
            return JsonResponse({"detail": "Source job belongs to another department."}, status=400)
        if data.get("source_job") and int(data["source_job"]) != issue.job_id:
            return JsonResponse({"detail": "Source job must match the selected material issue."}, status=400)
        sheet_area = material.sheet_area_sqft
        if sheet_area <= 0:
            return JsonResponse({"detail": "The material master must have valid sheet dimensions."}, status=400)
        already_registered = ReusableOffcut.objects.filter(source_issue=issue).aggregate(total=Sum("usable_area_sqft"))["total"] or Decimal("0")
        issue_area_available = max(issue.quantity - issue.returned_quantity - issue.wastage_quantity, Decimal("0")) * sheet_area
        if already_registered + usable_area > issue_area_available:
            return JsonResponse({"detail": f"Registered offcut area would exceed the source issue's available sheet area ({max(issue_area_available - already_registered, Decimal('0'))} sq ft remaining)."}, status=400)
        cost_per_sqft = issue.stock_lot.unit_cost / sheet_area
        offcut = ReusableOffcut.objects.create(
            material=material, department=department, location=location,
            thickness_mm=data.get("thickness_mm") or material.thickness_mm,
            length_mm=length_mm, width_mm=width_mm, usable_area_sqft=usable_area,
            source_issue=issue, source_lot=issue.stock_lot, cost_per_sqft=cost_per_sqft,
            source_job=issue.job, notes=str(data.get("notes", "")).strip(), created_by=request.user,
        )
        return JsonResponse({
            "ok": True, "id": offcut.pk, "status": offcut.status,
            "usable_area_sqft": str(offcut.usable_area_sqft),
            "cost_per_sqft": str(offcut.cost_per_sqft),
        }, status=201)
    except (ValueError, TypeError, InvalidOperation, Department.DoesNotExist,
            MaterialVariant.DoesNotExist, MaterialIssue.DoesNotExist, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_POST
@login_required
@transaction.atomic
def offcut_action_api(request, pk):
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        qs = ReusableOffcut.objects.select_for_update().select_related("material", "source_lot")
        if scope is not None:
            if not scope:
                return JsonResponse({"detail": "You do not have permission to manage offcuts."}, status=403)
            qs = qs.filter(department_id=scope)
        offcut = qs.get(pk=pk)
        if offcut.status != ReusableOffcut.Status.AVAILABLE:
            return JsonResponse({"detail": "Only available offcuts can be used or discarded."}, status=400)
        used_area = OffcutUsage.objects.filter(offcut=offcut).aggregate(total=Sum("used_area_sqft"))["total"] or Decimal("0")
        remaining_area = max(offcut.usable_area_sqft - used_area, Decimal("0"))
        action = data.get("action")
        if action == "used":
            from production.models import ProductionMaterial
            job = ProductionJob.objects.select_related("order__customer").get(pk=data.get("job"))
            line = ProductionMaterial.objects.select_for_update().select_related("material_variant").get(
                pk=data.get("material_line"), job=job
            )
            if job.order.customer.department_id != offcut.department_id:
                return JsonResponse({"detail": "Target job belongs to another department."}, status=400)
            if line.material_variant_id != offcut.material_id:
                return JsonResponse({"detail": "Target production material must match the offcut material."}, status=400)
            area = Decimal(str(data.get("used_area_sqft", remaining_area)))
            if area <= 0 or area > remaining_area:
                return JsonResponse({"detail": f"Usage must be greater than zero and no more than {remaining_area} sq ft."}, status=400)
            if offcut.cost_per_sqft is None:
                return JsonResponse({"detail": "This offcut has no source-batch cost snapshot and cannot be costed for production."}, status=400)
            total_cost = (area * offcut.cost_per_sqft).quantize(Decimal("0.01"))
            OffcutUsage.objects.create(
                offcut=offcut, target_job=job, target_material=line,
                used_area_sqft=area, cost_per_sqft=offcut.cost_per_sqft,
                total_cost=total_cost, created_by=request.user,
            )
            offcut.used_for_job = job
            if area == remaining_area:
                offcut.status = ReusableOffcut.Status.USED
            offcut.save(update_fields=["status", "used_for_job", "updated_at"])
            return JsonResponse({
                "ok": True, "id": offcut.pk, "status": offcut.status,
                "used_area_sqft": str(area), "remaining_area_sqft": str(remaining_area - area),
                "cost_per_sqft": str(offcut.cost_per_sqft), "allocated_cost": str(total_cost),
            })
        if action == "discarded":
            offcut.status = ReusableOffcut.Status.DISCARDED
        else:
            return JsonResponse({"detail": "Action must be 'used' or 'discarded'."}, status=400)
        offcut.save(update_fields=["status", "used_for_job", "updated_at"])
        return JsonResponse({"ok": True, "id": offcut.pk, "status": offcut.status})
    except (ValueError, TypeError, InvalidOperation, ReusableOffcut.DoesNotExist,
            ProductionJob.DoesNotExist, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_POST
@login_required
def production_material_issue_api(request):
    from .services import issue_material
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        if scope is False:
            return JsonResponse({"detail": "You do not have permission to issue material."}, status=403)
        from production.models import ProductionMaterial
        lines = ProductionMaterial.objects.select_related("job__order__customer")
        if scope is not None:
            lines = lines.filter(job__order__customer__department_id=scope)
        line = lines.filter(pk=data.get("material_line")).first()
        if not line:
            return JsonResponse({"detail": "Production material line not found in your department."}, status=404)
        employee = StaffProfile.objects.filter(pk=data.get("employee")).first() if data.get("employee") else None
        if data.get("employee") and not employee:
            return JsonResponse({"detail": "Employee not found."}, status=404)
        issue, movement = issue_material(
            material_id=line.pk,
            quantity=data.get("quantity"),
            balance_id=data.get("balance"),
            lot_id=data.get("lot"),
            user=request.user,
            employee=employee,
            reference=str(data.get("reference", "")),
            remarks=str(data.get("remarks", "")),
        )
        return JsonResponse({
            "ok": True, "issue_id": issue.pk, "movement_id": movement.pk,
            "issued_quantity": str(line.issued_quantity),
            "balance_after": str(movement.balance_after),
            "source_issue_id": movement.source_issue_id,
        }, status=201)
    except (ValueError, TypeError, InvalidOperation, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)



def _material_usage_adjustment(request, action):
    from production.models import ProductionMaterial
    from .services import return_issued_material, record_issued_wastage
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        if scope is False:
            return JsonResponse({"detail": "You do not have permission to adjust material usage."}, status=403)
        lines = ProductionMaterial.objects.select_related("job__order__customer")
        if scope is not None:
            lines = lines.filter(job__order__customer__department_id=scope)
        line = lines.filter(pk=data.get("material_line")).first()
        if not line:
            return JsonResponse({"detail": "Production material line not found in your department."}, status=404)
        employee = StaffProfile.objects.filter(pk=data.get("employee")).first() if data.get("employee") else None
        if data.get("employee") and not employee:
            return JsonResponse({"detail": "Employee not found."}, status=404)
        selected_issue = MaterialIssue.objects.filter(
            pk=data.get("material_issue"), material_id=line.pk, job_id=line.job_id
        ).first()
        if not selected_issue:
            return JsonResponse({"detail": "The selected material issue does not belong to this production material line."}, status=404)
        operation = return_issued_material if action == "return" else record_issued_wastage
        movement = operation(
            material_issue_id=selected_issue.pk, quantity=data.get("quantity"),
            user=request.user, employee=employee, reference=str(data.get("reference", "")),
            remarks=str(data.get("remarks", "")),
        )
        line.refresh_from_db()
        return JsonResponse({
            "ok": True, "movement_id": movement.pk,
            "issued_quantity": str(line.issued_quantity),
            "returned_quantity": str(line.returned_quantity),
            "wastage_quantity": str(line.wastage_quantity),
            "actual_consumption": str(line.actual_consumption),
            "balance_after": str(movement.balance_after),
        }, status=201)
    except (ValueError, TypeError, InvalidOperation, ValidationError,
            MaterialStockBalance.DoesNotExist, ProductionMaterial.DoesNotExist, MaterialIssue.DoesNotExist) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_POST
@login_required
def production_material_return_api(request):
    return _material_usage_adjustment(request, "return")


@require_POST
@login_required
def production_material_wastage_api(request):
    return _material_usage_adjustment(request, "wastage")



@require_POST
@login_required
def offcut_create_api(request):
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        if scope is False:
            return JsonResponse({"detail": "You do not have permission to manage offcuts."}, status=403)
        department_id = scope if scope is not None else data.get("department")
        department = Department.objects.get(pk=department_id, is_active=True)
        material = MaterialVariant.objects.get(pk=data.get("material"), is_active=True)
        location = str(data.get("location", "")).strip()
        if not location:
            return JsonResponse({"detail": "Location is required."}, status=400)
        source_job = None
        if data.get("source_job"):
            source_job = ProductionJob.objects.select_related("order__customer").get(pk=data["source_job"])
            if source_job.order.customer.department_id != department.pk:
                return JsonResponse({"detail": "Source job belongs to another department."}, status=400)
        offcut = ReusableOffcut.objects.create(
            material=material, department=department, location=location,
            thickness_mm=data.get("thickness_mm") or material.thickness_mm,
            length_mm=data.get("length_mm"), width_mm=data.get("width_mm"),
            usable_area_sqft=data.get("usable_area_sqft"), source_job=source_job,
            notes=str(data.get("notes", "")).strip(), created_by=request.user,
        )
        return JsonResponse({"ok": True, "id": offcut.pk, "status": offcut.status}, status=201)
    except (ValueError, TypeError, InvalidOperation, Department.DoesNotExist,
            MaterialVariant.DoesNotExist, ProductionJob.DoesNotExist) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_POST
@login_required
@transaction.atomic
def offcut_action_api(request, pk):
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        qs = ReusableOffcut.objects.select_for_update()
        if scope is not None:
            if not scope:
                return JsonResponse({"detail": "You do not have permission to manage offcuts."}, status=403)
            qs = qs.filter(department_id=scope)
        offcut = qs.get(pk=pk)
        if offcut.status != ReusableOffcut.Status.AVAILABLE:
            return JsonResponse({"detail": "Only available offcuts can be used or discarded."}, status=400)
        action = data.get("action")
        if action == "used":
            job = ProductionJob.objects.select_related("order__customer").get(pk=data.get("job"))
            if job.order.customer.department_id != offcut.department_id:
                return JsonResponse({"detail": "Target job belongs to another department."}, status=400)
            offcut.status = ReusableOffcut.Status.USED
            offcut.used_for_job = job
        elif action == "discarded":
            offcut.status = ReusableOffcut.Status.DISCARDED
        else:
            return JsonResponse({"detail": "Action must be 'used' or 'discarded'."}, status=400)
        offcut.save(update_fields=["status", "used_for_job", "updated_at"])
        return JsonResponse({"ok": True, "id": offcut.pk, "status": offcut.status})
    except (ValueError, TypeError, ReusableOffcut.DoesNotExist, ProductionJob.DoesNotExist) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_GET
@login_required
def material_stock_counts_api(request):
    scope = _manager_department(request.user)
    qs = MaterialStockCount.objects.select_related("balance__material", "balance__department", "submitted_by", "reviewed_by")
    if scope is not None:
        qs = qs.filter(balance__department_id=scope) if scope else qs.none()
    return JsonResponse({"items": [{
        "id": x.pk, "balance_id": x.balance_id, "material": str(x.balance.material),
        "department": x.balance.department.name, "location": x.balance.location,
        "system_quantity": str(x.system_quantity), "counted_quantity": str(x.counted_quantity),
        "variance": str(x.variance), "status": x.status, "reason": x.reason,
        "submitted_by": x.submitted_by.username if x.submitted_by_id else None,
        "reviewed_by": x.reviewed_by.username if x.reviewed_by_id else None,
        "created_at": x.created_at.isoformat(), "reviewed_at": x.reviewed_at.isoformat() if x.reviewed_at else None,
    } for x in qs[:500]]})


@require_POST
@login_required
def material_stock_count_submit_api(request):
    from .services import submit_material_stock_count
    try:
        data = json.loads(request.body or "{}")
        scope = _manager_department(request.user)
        if scope is False:
            return JsonResponse({"detail": "You do not have permission to submit stock counts."}, status=403)
        balance = _visible_balances(request.user).get(pk=data.get("balance"))
        count = submit_material_stock_count(
            balance_id=balance.pk, counted_quantity=data.get("counted_quantity"),
            user=request.user, reason=str(data.get("reason", "")),
        )
        return JsonResponse({
            "ok": True, "id": count.pk, "system_quantity": str(count.system_quantity),
            "counted_quantity": str(count.counted_quantity), "variance": str(count.variance),
            "status": count.status,
        }, status=201)
    except (ValueError, TypeError, InvalidOperation, MaterialStockBalance.DoesNotExist, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@require_POST
@login_required
def material_stock_count_review_api(request, pk):
    from .services import review_material_stock_count
    scope = _manager_department(request.user)
    if scope is not None:
        return JsonResponse({"detail": "Only Founder/Admin can approve or reject stock count variances."}, status=403)
    try:
        data = json.loads(request.body or "{}")
        if not isinstance(data.get("approve"), bool):
            return JsonResponse({"detail": "approve must be true or false."}, status=400)
        count = review_material_stock_count(
            count_id=pk, approve=data["approve"], user=request.user,
            review_note=str(data.get("review_note", "")),
        )
        return JsonResponse({
            "ok": True, "id": count.pk, "status": count.status,
            "correction_movement_id": count.correction_movement_id,
        })
    except (ValueError, TypeError, MaterialStockCount.DoesNotExist, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
