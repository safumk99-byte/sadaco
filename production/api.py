import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserProfile
from sales.models import SalesOrder, DesignApproval
from staff.models import StaffProfile
from products.models import Product, MaterialVariant
from .forms import ProductionJobForm, ProductionProgressForm, ProductionMaterialForm, ProductionIssueForm
from .models import ProductionJob, ProductionProgress, ProductionMaterial, ProductionIssue

MANAGER_ROLES = {UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER}

def _active_profile(user):
    profile = getattr(user, "profile", None)
    return profile if profile and profile.is_active else None


def _manager(user):
    profile = _active_profile(user)
    return user.is_superuser or bool(profile and profile.role in MANAGER_ROLES)


def _global_admin(user):
    profile = _active_profile(user)
    return user.is_superuser or bool(
        profile and profile.role in (UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN)
    )


def _manager_department_id(user):
    profile = getattr(user, "profile", None)
    return profile.department_id if profile and profile.role == UserProfile.Role.MANAGER else None


def _department_jobs(qs, department_id):
    if not department_id:
        return qs.none()
    return qs.filter(order__customer__department_id=department_id)


def _visible_jobs(user):
    qs = ProductionJob.objects.select_related('order__customer', 'assigned_staff__user', 'created_by')
    if _global_admin(user):
        return qs
    if getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.MANAGER:
        return _department_jobs(qs, _manager_department_id(user))
    return qs.filter(assigned_staff__user=user)


def _job_visible(user, job):
    if _global_admin(user):
        return True
    if getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.MANAGER:
        department_id = _manager_department_id(user)
        return bool(department_id and job.order.customer.department_id == department_id)
    return job.assigned_staff_id == getattr(getattr(user, 'staff_profile', None), 'id', None)


def _staff_in_manager_department(user, staff):
    if _global_admin(user):
        return True
    if getattr(getattr(user, "profile", None), "role", None) != UserProfile.Role.MANAGER:
        return False
    department_id = _manager_department_id(user)
    return bool(department_id and staff and staff.department_id == department_id)

def _choices(choices):
    return [{'value': v, 'label': l} for v, l in choices]

def _job(j):
    return {
        'id': j.id, 'job_no': j.job_no,
        'order': {'id': j.order_id, 'order_no': j.order.order_no, 'customer': j.order.customer.name,
                  'item_description': j.order.item_description, 'quantity': str(j.order.quantity)},
        'station': j.station, 'station_label': j.get_station_display(),
        'stage': j.stage, 'stage_label': j.get_stage_display(),
        'status': j.status, 'status_label': j.get_status_display(),
        'assigned_staff': {'id': j.assigned_staff_id, 'name': str(j.assigned_staff)} if j.assigned_staff else None,
        'priority': j.priority, 'priority_label': j.get_priority_display(),
        'deadline': j.deadline.isoformat() if j.deadline else None,
        'progress_percent': j.progress_percent,
        'safety_checked': j.safety_checked, 'design_checked': j.design_checked, 'material_ready': j.material_ready,
        'started_at': j.started_at.isoformat() if j.started_at else None,
        'completed_at': j.completed_at.isoformat() if j.completed_at else None,
        'notes': j.notes, 'created_at': j.created_at.isoformat(), 'updated_at': j.updated_at.isoformat(),
    }

def _progress(p):
    return {'id': p.id, 'stage': p.stage, 'stage_label': p.get_stage_display(), 'progress_percent': p.progress_percent,
            'note': p.note, 'updated_by': p.updated_by.get_full_name() if p.updated_by else None,
            'created_at': p.created_at.isoformat()}

def _material(m):
    return {'id': m.id, 'product': {'id': m.product_id, 'name': m.product.name} if m.product else None,
            'material_name': m.material_name, 'material_variant_id': m.material_variant_id, 'quantity_required': str(m.quantity_required), 'unit': m.unit,
            'issued_quantity': str(m.issued_quantity), 'pending_quantity': str(m.pending_quantity), 'notes': m.notes}

def _issue(i):
    return {'id': i.id, 'issue_type': i.issue_type, 'issue_type_label': i.get_issue_type_display(), 'stage': i.stage,
            'stage_label': i.get_stage_display(), 'reason': i.reason, 'corrective_action': i.corrective_action,
            'staff': str(i.staff) if i.staff else None, 'occurred_at': i.occurred_at.isoformat(), 'resolved': i.resolved,
            'resolved_at': i.resolved_at.isoformat() if i.resolved_at else None}

@require_GET
@login_required
def summary(request):
    qs = _visible_jobs(request.user)
    return JsonResponse({'stats': {
        'total': qs.count(),
        'pending': qs.filter(status__in=[ProductionJob.Status.PENDING, ProductionJob.Status.ASSIGNED]).count(),
        'active': qs.filter(status=ProductionJob.Status.IN_PROGRESS).count(),
        'on_hold': qs.filter(status=ProductionJob.Status.ON_HOLD).count(),
        'completed': qs.filter(status=ProductionJob.Status.COMPLETED).count(),
        'delayed': qs.filter(deadline__lt=timezone.localdate()).exclude(status__in=[ProductionJob.Status.COMPLETED, ProductionJob.Status.CANCELLED]).count(),
    }})

@require_GET
@login_required
def jobs(request):
    qs = _visible_jobs(request.user)
    q = request.GET.get('q', '').strip(); status = request.GET.get('status', '').strip(); station = request.GET.get('station', '').strip()
    if q: qs = qs.filter(Q(job_no__icontains=q) | Q(order__order_no__icontains=q) | Q(order__customer__name__icontains=q) | Q(order__item_description__icontains=q))
    if status: qs = qs.filter(status=status)
    if station: qs = qs.filter(station=station)
    return JsonResponse({'jobs': [_job(x) for x in qs[:300]], 'can_manage': _manager(request.user),
        'statuses': _choices(ProductionJob.Status.choices), 'stations': _choices(ProductionJob.Station.choices),
        'stages': _choices(ProductionJob.Stage.choices), 'priorities': _choices([('normal','Normal'),('high','High'),('urgent','Urgent')])})

@require_GET
@login_required
def options(request):
    staff = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).select_related('user', 'department')
    orders = SalesOrder.objects.select_related('customer', 'responsible_staff').filter(status__in=[SalesOrder.Status.CONFIRMED, SalesOrder.Status.PRODUCTION_PENDING]).order_by('-created_at')
    if not _global_admin(request.user):
        department_id = _manager_department_id(request.user)
        staff = staff.filter(department_id=department_id) if department_id else staff.none()
        orders = orders.filter(customer__department_id=department_id) if department_id else orders.none()
    orders = orders[:200]
    products = Product.objects.filter(status=Product.Status.ACTIVE).order_by('name')[:300]
    return JsonResponse({'staff': [{'id': s.id, 'name': str(s)} for s in staff],
        'orders': [{'id': o.id, 'order_no': o.order_no, 'customer': o.customer.name, 'item_description': o.item_description, 'deadline': o.deadline.isoformat() if o.deadline else None} for o in orders],
        'products': [{'id': p.id, 'name': p.name, 'sku': p.sku} for p in products],
        'materials': [{'id': m.id, 'name': m.material_name, 'brand': m.brand, 'thickness_mm': str(m.thickness_mm) if m.thickness_mm is not None else None, 'unit': m.unit} for m in MaterialVariant.objects.filter(is_active=True).order_by('material_name', 'brand', 'thickness_mm')[:500]]})

@require_GET
@login_required
def _job_material_cost_summary(job):
    """Calculate receipt-backed material cost with offcut asset transfers and write-offs."""
    from decimal import Decimal
    from inventory.models import MaterialIssue, ReusableOffcut, OffcutUsage

    money = Decimal("0.01")
    issues = MaterialIssue.objects.filter(job_id=job.pk, unit_rate__isnull=False)
    issued_cost = sum((row.quantity * row.unit_rate for row in issues), Decimal("0"))
    returned_cost = sum((row.returned_quantity * row.unit_rate for row in issues), Decimal("0"))

    generated = ReusableOffcut.objects.filter(source_job_id=job.pk, cost_per_sqft__isnull=False)
    salvage_credit = sum((row.usable_area_sqft * row.cost_per_sqft for row in generated), Decimal("0"))
    discarded_writeoff = sum((row.discarded_cost for row in generated), Decimal("0"))
    registered_area = sum((row.usable_area_sqft for row in generated), Decimal("0"))
    discarded_area = sum((row.discarded_area_sqft for row in generated), Decimal("0"))
    generated_used_area = sum((
        usage.used_area_sqft
        for usage in OffcutUsage.objects.filter(offcut__in=generated)
    ), Decimal("0"))
    inventory_value = sum((
        max(row.usable_area_sqft - row.discarded_area_sqft - sum(
            (usage.used_area_sqft for usage in row.usages.all()), Decimal("0")
        ), Decimal("0")) * row.cost_per_sqft
        for row in generated
    ), Decimal("0"))

    target_usages = OffcutUsage.objects.filter(target_job_id=job.pk)
    consumed_offcut_cost = sum((row.total_cost for row in target_usages), Decimal("0"))
    consumed_offcut_area = sum((row.used_area_sqft for row in target_usages), Decimal("0"))
    net_cost = issued_cost - returned_cost - salvage_credit + discarded_writeoff + consumed_offcut_cost
    return {
        "currency": "INR",
        "issued_material_cost": str(issued_cost.quantize(money)),
        "returned_material_credit": str(returned_cost.quantize(money)),
        "offcut_salvage_credit": str(salvage_credit.quantize(money)),
        "offcut_discard_writeoff": str(discarded_writeoff.quantize(money)),
        "offcut_consumed_cost": str(consumed_offcut_cost.quantize(money)),
        "offcut_inventory_value": str(inventory_value.quantize(money)),
        "net_material_cost": str(net_cost.quantize(money)),
        "offcut_registered_area_sqft": str(registered_area.quantize(Decimal("0.0001"))),
        "generated_offcut_transferred_area_sqft": str(generated_used_area.quantize(Decimal("0.0001"))),
        "offcut_consumed_here_area_sqft": str(consumed_offcut_area.quantize(Decimal("0.0001"))),
        "offcut_discarded_area_sqft": str(discarded_area.quantize(Decimal("0.0001"))),
        "unpriced_issue_count": MaterialIssue.objects.filter(job_id=job.pk, unit_rate__isnull=True).count(),
    }


def detail(request, pk):
    job = get_object_or_404(_visible_jobs(request.user).prefetch_related('progress_updates__updated_by', 'materials__product', 'issues__staff'), pk=pk)
    if not _job_visible(request.user, job): raise PermissionDenied
    from inventory.models import MaterialIssue
    material_issues = MaterialIssue.objects.filter(job_id=job.pk).select_related(
        "material", "stock_lot__receipt_line__receipt"
    ).order_by("-issued_at", "-pk")
    issue_rows = [{
        "id": item.pk,
        "material_line": item.material_id,
        "material_variant_id": item.material.material_variant_id,
        "material_name": item.material.material_name,
        "quantity": str(item.quantity),
        "returned_quantity": str(item.returned_quantity),
        "wastage_quantity": str(item.wastage_quantity),
        "remaining_quantity": str(item.quantity - item.returned_quantity - item.wastage_quantity),
        "unit": item.material.unit,
        "unit_rate": str(item.unit_rate) if item.unit_rate is not None else None,
        "receipt_no": item.stock_lot.receipt_line.receipt.receipt_no if item.stock_lot_id else None,
        "issued_at": item.issued_at.isoformat(),
        "trackable": bool(item.stock_lot_id and item.unit_rate is not None),
    } for item in material_issues]
    return JsonResponse({'job': _job(job), 'progress': [_progress(x) for x in job.progress_updates.all()],
        'materials': [_material(x) for x in job.materials.all()], 'issues': [_issue(x) for x in job.issues.all()],
        'material_issues': issue_rows,
        'material_costs': _job_material_cost_summary(job) if _manager(request.user) else None,
        'can_manage': _manager(request.user)})

def _data(request):
    try: return json.loads(request.body or '{}')
    except (TypeError, ValueError): return {}

@require_POST
@login_required
def create(request):
    if not _manager(request.user): raise PermissionDenied
    data = _data(request); order_id = data.get('order')
    order_qs = SalesOrder.objects.select_related('quotation', 'responsible_staff')
    if not _global_admin(request.user):
        department_id = _manager_department_id(request.user)
        order_qs = order_qs.filter(customer__department_id=department_id) if department_id else order_qs.none()
    order = get_object_or_404(order_qs, pk=order_id)
    if order.status not in (SalesOrder.Status.PRODUCTION_PENDING, SalesOrder.Status.CONFIRMED):
        return JsonResponse({'detail': 'This order is not ready for production planning.'}, status=400)
    latest_design = order.quotation.designs.filter(status=DesignApproval.Status.APPROVED).first() if order.quotation_id else None
    if not latest_design:
        return JsonResponse({'detail': 'Production can start only after customer design approval.'}, status=400)
    if ProductionJob.objects.filter(order=order, status__in=[ProductionJob.Status.PENDING, ProductionJob.Status.ASSIGNED, ProductionJob.Status.IN_PROGRESS, ProductionJob.Status.ON_HOLD]).exists():
        return JsonResponse({'detail': 'An active production job already exists for this order.'}, status=400)
    form = ProductionJobForm(data)
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()}, status=400)
    assigned_staff = form.cleaned_data.get("assigned_staff")
    if assigned_staff and not _staff_in_manager_department(request.user, assigned_staff):
        return JsonResponse({"detail": "You can only assign jobs to staff in your own department."}, status=403)
    job = form.save(commit=False); job.order=order; job.created_by=request.user; job.save()
    order.status = SalesOrder.Status.PRODUCTION_PENDING; order.save(update_fields=['status','updated_at'])
    return JsonResponse({'job': _job(job)}, status=201)

@require_POST
@login_required
def update(request, pk):
    if not _manager(request.user):
        raise PermissionDenied
    job = get_object_or_404(_visible_jobs(request.user), pk=pk)
    if not _job_visible(request.user, job): raise PermissionDenied
    data = _data(request)
    # Reject lifecycle finalization from the raw request before ModelForm/model.save
    # can normalize a completed job to 100 percent.
    if (
        data.get("status") == ProductionJob.Status.COMPLETED
        or data.get("stage") == ProductionJob.Stage.COMPLETED
    ) and not (
        job.status == ProductionJob.Status.COMPLETED
        and job.stage == ProductionJob.Stage.COMPLETED
    ):
        return JsonResponse({"detail": "Production jobs can only be finalized after a passing Final QC result in the Quality module."}, status=400)
    form = ProductionJobForm(data, instance=job)
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()}, status=400)
    assigned_staff = form.cleaned_data.get("assigned_staff")
    if assigned_staff and not _staff_in_manager_department(request.user, assigned_staff):
        return JsonResponse({"detail": "You can only assign jobs to staff in your own department."}, status=403)
    requested_status = form.cleaned_data["status"]
    requested_stage = form.cleaned_data["stage"]
    if (
        requested_status == ProductionJob.Status.COMPLETED
        or requested_stage == ProductionJob.Stage.COMPLETED
    ) and not (
        job.status == ProductionJob.Status.COMPLETED
        and job.stage == ProductionJob.Stage.COMPLETED
        and requested_status == job.status
        and requested_stage == job.stage
    ):
        return JsonResponse({"detail": "Production jobs can only be finalized after a passing Final QC result in the Quality module."}, status=400)
    job = form.save()
    return JsonResponse({'job': _job(job)})

@require_POST
@login_required
def add_progress(request, pk):
    job = get_object_or_404(ProductionJob, pk=pk)
    if not _job_visible(request.user, job): raise PermissionDenied
    form = ProductionProgressForm(_data(request))
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()}, status=400)
    progress_percent = form.cleaned_data["progress_percent"]
    progress_stage = form.cleaned_data["stage"]
    if not _manager(request.user) and (
        progress_percent >= 100 or progress_stage == ProductionJob.Stage.COMPLETED
    ):
        return JsonResponse({"detail": "Only a manager can finalize a production job. Staff can report progress up to 99%."}, status=403)
    if progress_percent >= 100 or progress_stage == ProductionJob.Stage.COMPLETED:
        return JsonResponse({"detail": "Final production completion is recorded only after a passing Final QC result in the Quality module."}, status=400)
    update_obj = form.save(commit=False); update_obj.job=job; update_obj.updated_by=request.user; update_obj.save()
    job.stage=update_obj.stage; job.progress_percent=update_obj.progress_percent
    if update_obj.progress_percent >= 100: job.status=ProductionJob.Status.COMPLETED
    elif job.status in (ProductionJob.Status.PENDING, ProductionJob.Status.ASSIGNED, ProductionJob.Status.ON_HOLD): job.status=ProductionJob.Status.IN_PROGRESS
    job.save()
    if update_obj.progress_percent > 0 and job.order.status in (
        SalesOrder.Status.CONFIRMED, SalesOrder.Status.PRODUCTION_PENDING
    ):
        job.order.status=SalesOrder.Status.IN_PRODUCTION; job.order.save(update_fields=['status','updated_at'])
    return JsonResponse({'job': _job(job), 'progress': _progress(update_obj)})

@require_POST
@login_required
def add_material(request, pk):
    if not _manager(request.user): raise PermissionDenied
    job=get_object_or_404(_visible_jobs(request.user),pk=pk); form=ProductionMaterialForm(_data(request))
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    obj=form.save(commit=False); obj.job=job; obj.save(); return JsonResponse({'material':_material(obj)},status=201)

@require_POST
@login_required
def add_issue(request, pk):
    job=get_object_or_404(ProductionJob,pk=pk)
    if not _job_visible(request.user,job): raise PermissionDenied
    form=ProductionIssueForm(_data(request))
    if not _global_admin(request.user):
        department_id = job.order.customer.department_id
        form.fields["staff"].queryset = StaffProfile.objects.filter(department_id=department_id) if department_id else StaffProfile.objects.none()
    if not form.is_valid(): return JsonResponse({'detail':'Validation failed.','errors':form.errors.get_json_data()},status=400)
    obj=form.save(commit=False); obj.job=job; obj.created_by=request.user; obj.save()
    if obj.issue_type == ProductionIssue.Type.DELAY: job.status=ProductionJob.Status.ON_HOLD; job.save(update_fields=['status','updated_at'])
    return JsonResponse({'issue':_issue(obj), 'job':_job(job)},status=201)
