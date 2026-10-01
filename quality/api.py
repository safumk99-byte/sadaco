import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserProfile
from production.models import ProductionJob
from staff.models import StaffProfile
from .forms import QualityCheckForm, ReworkRecordForm, PackingRecordForm
from .models import QualityCheck, ReworkRecord, PackingRecord



def _is_manager(user):
    return user.is_superuser or getattr(getattr(user, "profile", None), "role", None) in ("super_admin", "institution_admin", "manager")

def _visible_job(user, job):
    return _is_manager(user) or (hasattr(user, "staff_profile") and job.assigned_staff_id == user.staff_profile.id)

def _notify(job, title, message, priority="normal"):
    from accounts.models import Notification, UserProfile
    users=[]
    if job.assigned_staff_id: users.append(job.assigned_staff.user)
    if job.created_by_id: users.append(job.created_by)
    users += list(UserProfile.objects.filter(role__in=[UserProfile.Role.SUPER_ADMIN,UserProfile.Role.INSTITUTION_ADMIN,UserProfile.Role.MANAGER],is_active=True).values_list("user",flat=True))
    seen=set()
    for item in users:
        uid=getattr(item,"pk",item)
        if uid in seen: continue
        seen.add(uid)
        Notification.objects.create(user_id=uid,notification_type=Notification.Type.TASK,priority=priority,title=title,message=message,url=f"/quality/jobs/{job.pk}/")

def _sync_job(job):
    from production.models import ProductionJob
    from sales.models import SalesOrder
    latest_final=job.quality_checks.filter(check_type=QualityCheck.CheckType.FINAL).first()
    open_rework=job.rework_records.exclude(status=ReworkRecord.Status.COMPLETED).exclude(status=ReworkRecord.Status.CANCELLED).exists()
    if open_rework or (latest_final and latest_final.result in (QualityCheck.Result.FAIL,QualityCheck.Result.REWORK)):
        job.status=ProductionJob.Status.ON_HOLD; job.stage=ProductionJob.Stage.QC_PENDING; job.save(update_fields=["status","stage","updated_at"])
        if job.order.status != SalesOrder.Status.IN_PRODUCTION:
            job.order.status=SalesOrder.Status.IN_PRODUCTION; job.order.save(update_fields=["status","updated_at"])
        return
    if latest_final and latest_final.result == QualityCheck.Result.PASS:
        job.stage=ProductionJob.Stage.COMPLETED; job.status=ProductionJob.Status.COMPLETED; job.progress_percent=100; job.save(update_fields=["stage","status","progress_percent","updated_at"])
        if job.order.status != SalesOrder.Status.READY:
            job.order.status=SalesOrder.Status.READY; job.order.save(update_fields=["status","updated_at"])
        PackingRecord.objects.get_or_create(job=job); return
    job.stage=ProductionJob.Stage.QC_PENDING; job.save(update_fields=["stage","updated_at"])

def _data(request):
    try:
        return json.loads(request.body or "{}")
    except (TypeError, ValueError):
        return {}


def _choices(choices):
    return [{"value": value, "label": label} for value, label in choices]


def _staff_name(staff):
    if not staff:
        return None
    return staff.user.get_full_name() or staff.user.username


def _check(c):
    return {
        "id": c.id,
        "job_id": c.job_id,
        "job_no": c.job.job_no,
        "order_no": c.job.order.order_no,
        "customer": c.job.order.customer.name,
        "check_type": c.check_type,
        "check_type_label": c.get_check_type_display(),
        "result": c.result,
        "result_label": c.get_result_display(),
        "inspector": {"id": c.inspector_id, "name": _staff_name(c.inspector)} if c.inspector else None,
        "stage": c.stage,
        "design_match": c.design_match,
        "measurement_ok": c.measurement_ok,
        "finishing_ok": c.finishing_ok,
        "colour_ok": c.colour_ok,
        "engraving_ok": c.engraving_ok,
        "defects": c.defects,
        "rework_reason": c.rework_reason,
        "corrective_action": c.corrective_action,
        "rework_count": c.rework_count,
        "remarks": c.remarks,
        "checked_at": c.checked_at.isoformat() if c.checked_at else None,
        "created_at": c.created_at.isoformat(),
    }


def _rework(r):
    return {
        "id": r.id,
        "quality_check_id": r.quality_check_id,
        "job_id": r.job_id,
        "reason": r.reason,
        "corrective_action": r.corrective_action,
        "assigned_staff": {"id": r.assigned_staff_id, "name": _staff_name(r.assigned_staff)} if r.assigned_staff else None,
        "status": r.status,
        "status_label": r.get_status_display(),
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at": r.created_at.isoformat(),
    }


def _packing(p):
    if not p:
        return None
    return {
        "id": p.id,
        "job_id": p.job_id,
        "packing_material": p.packing_material,
        "fragile_protection": p.fragile_protection,
        "customer_label": p.customer_label,
        "status": p.status,
        "status_label": p.get_status_display(),
        "packed_by": {"id": p.packed_by_id, "name": _staff_name(p.packed_by)} if p.packed_by else None,
        "packed_at": p.packed_at.isoformat() if p.packed_at else None,
        "notes": p.notes,
    }


def _job(j):
    latest = j.quality_checks.first()
    return {
        "id": j.id,
        "job_no": j.job_no,
        "order": {"id": j.order_id, "order_no": j.order.order_no, "customer": j.order.customer.name, "item_description": j.order.item_description, "quantity": str(j.order.quantity)},
        "station": j.station,
        "station_label": j.get_station_display(),
        "stage": j.stage,
        "stage_label": j.get_stage_display(),
        "status": j.status,
        "status_label": j.get_status_display(),
        "assigned_staff": {"id": j.assigned_staff_id, "name": _staff_name(j.assigned_staff)} if j.assigned_staff else None,
        "deadline": j.deadline.isoformat() if j.deadline else None,
        "progress_percent": j.progress_percent,
        "latest_result": latest.result if latest else None,
        "latest_result_label": latest.get_result_display() if latest else None,
    }


@require_GET
@login_required
def summary(request):
    if not _is_manager(request.user):
        raise PermissionDenied
    return JsonResponse({
        "stats": {
            "pending": ProductionJob.objects.filter(stage=ProductionJob.Stage.QC_PENDING).exclude(status=ProductionJob.Status.CANCELLED).count(),
            "passed": QualityCheck.objects.filter(result=QualityCheck.Result.PASS).count(),
            "rework": ReworkRecord.objects.filter(status__in=[ReworkRecord.Status.OPEN, ReworkRecord.Status.IN_PROGRESS]).count(),
            "packed": PackingRecord.objects.filter(status=PackingRecord.Status.PACKED).count(),
            "failed": QualityCheck.objects.filter(result=QualityCheck.Result.FAIL).count(),
        }
    })


@require_GET
@login_required
def checks(request):
    if not _is_manager(request.user):
        raise PermissionDenied
    qs = QualityCheck.objects.select_related("job__order__customer", "inspector__user")
    q = request.GET.get("q", "").strip()
    result = request.GET.get("result", "").strip()
    check_type = request.GET.get("check_type", "").strip()
    if q:
        qs = qs.filter(Q(job__job_no__icontains=q) | Q(job__order__order_no__icontains=q) | Q(job__order__customer__name__icontains=q))
    if result:
        qs = qs.filter(result=result)
    if check_type:
        qs = qs.filter(check_type=check_type)
    return JsonResponse({"checks": [_check(c) for c in qs[:200]]})


@require_GET
@login_required
def options(request):
    if not _is_manager(request.user):
        raise PermissionDenied
    staff = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).select_related("user")
    jobs = ProductionJob.objects.select_related("order__customer").filter(stage=ProductionJob.Stage.QC_PENDING).exclude(status=ProductionJob.Status.CANCELLED).order_by("deadline", "-created_at")[:300]
    return JsonResponse({
        "staff": [{"id": s.id, "name": str(s)} for s in staff],
        "jobs": [{"id": j.id, "job_no": j.job_no, "order_no": j.order.order_no, "customer": j.order.customer.name} for j in jobs],
        "check_types": _choices(QualityCheck.CheckType.choices),
        "results": _choices(QualityCheck.Result.choices),
        "rework_statuses": _choices(ReworkRecord.Status.choices),
        "packing_statuses": _choices(PackingRecord.Status.choices),
    })


@require_GET
@login_required
def detail(request, pk):
    job = get_object_or_404(ProductionJob.objects.select_related("order__customer", "assigned_staff__user").prefetch_related("quality_checks__inspector__user", "rework_records__assigned_staff__user", "packing"), pk=pk)
    if not _visible_job(request.user, job):
        raise PermissionDenied
    return JsonResponse({
        "job": _job(job),
        "checks": [_check(c) for c in job.quality_checks.all()],
        "reworks": [_rework(r) for r in job.rework_records.all()],
        "packing": _packing(getattr(job, "packing", None)),
        "can_manage": _is_manager(request.user),
    })


@require_POST
@login_required
def create_check(request):
    data = _data(request)
    job = get_object_or_404(ProductionJob, pk=data.get("job"))
    if not _visible_job(request.user, job):
        raise PermissionDenied
    form = QualityCheckForm(data)
    if not form.is_valid():
        return JsonResponse({"detail": "Validation failed.", "errors": form.errors.get_json_data()}, status=400)
    check = form.save(commit=False)
    check.job = job
    check.created_by = request.user
    if not check.inspector and hasattr(request.user, "staff_profile"):
        check.inspector = request.user.staff_profile
    check.rework_count = job.rework_records.count()
    check.save()
    if check.result in (QualityCheck.Result.FAIL, QualityCheck.Result.REWORK):
        job.stage = ProductionJob.Stage.QC_PENDING
        job.status = ProductionJob.Status.ON_HOLD
        job.save(update_fields=["stage", "status", "updated_at"])
        _notify(job, "Quality issue recorded", f"{job.job_no}: {check.get_result_display()}")
    elif check.result == QualityCheck.Result.PASS:
        _sync_job(job)
        _notify(job, "Quality check passed", f"{job.job_no} passed {check.get_check_type_display()}.")
    else:
        job.stage = ProductionJob.Stage.QC_PENDING
        job.save(update_fields=["stage", "updated_at"])
    return JsonResponse({"check": _check(check)}, status=201)


@require_POST
@login_required
def update_check(request, pk):
    check = get_object_or_404(QualityCheck.objects.select_related("job"), pk=pk)
    if not _visible_job(request.user, check.job):
        raise PermissionDenied
    form = QualityCheckForm(_data(request), instance=check)
    if not form.is_valid():
        return JsonResponse({"detail": "Validation failed.", "errors": form.errors.get_json_data()}, status=400)
    check = form.save()
    _sync_job(check.job)
    return JsonResponse({"check": _check(check)})


@require_POST
@login_required
def create_rework(request, check_id):
    check = get_object_or_404(QualityCheck.objects.select_related("job"), pk=check_id)
    if not _visible_job(request.user, check.job):
        raise PermissionDenied
    form = ReworkRecordForm(_data(request))
    if not form.is_valid():
        return JsonResponse({"detail": "Validation failed.", "errors": form.errors.get_json_data()}, status=400)
    rework = form.save(commit=False)
    rework.quality_check = check
    rework.job = check.job
    rework.created_by = request.user
    rework.save()
    check.result = QualityCheck.Result.REWORK
    check.rework_count = check.job.rework_records.count()
    check.save(update_fields=["result", "rework_count", "updated_at"])
    job = check.job
    job.status = ProductionJob.Status.ON_HOLD
    job.stage = ProductionJob.Stage.QC_PENDING
    job.save(update_fields=["status", "stage", "updated_at"])
    _notify(job, "Rework assigned", f"{job.job_no}: {rework.reason[:140]}")
    return JsonResponse({"rework": _rework(rework)}, status=201)


@require_POST
@login_required
def update_rework(request, pk):
    rework = get_object_or_404(ReworkRecord.objects.select_related("job"), pk=pk)
    if not _visible_job(request.user, rework.job):
        raise PermissionDenied
    form = ReworkRecordForm(_data(request), instance=rework)
    if not form.is_valid():
        return JsonResponse({"detail": "Validation failed.", "errors": form.errors.get_json_data()}, status=400)
    rework = form.save()
    if rework.status == ReworkRecord.Status.COMPLETED:
        rework.job.status = ProductionJob.Status.IN_PROGRESS
        rework.job.stage = ProductionJob.Stage.PRODUCTION
        rework.job.save(update_fields=["status", "stage", "updated_at"])
        _notify(rework.job, "Rework completed", f"{rework.job.job_no} rework was completed.")
    return JsonResponse({"rework": _rework(rework)})


@require_POST
@login_required
def update_packing(request, pk):
    job = get_object_or_404(ProductionJob, pk=pk)
    if not _is_manager(request.user) and not _visible_job(request.user, job):
        raise PermissionDenied
    if job.status != ProductionJob.Status.COMPLETED:
        return JsonResponse({"detail": "Packing is available only after final QC passes."}, status=400)
    packing, _ = PackingRecord.objects.get_or_create(job=job)
    form = PackingRecordForm(_data(request), instance=packing)
    if not form.is_valid():
        return JsonResponse({"detail": "Validation failed.", "errors": form.errors.get_json_data()}, status=400)
    packing = form.save()
    if packing.status == PackingRecord.Status.PACKED:
        from sales.models import SalesOrder
        job.order.status = SalesOrder.Status.READY
        job.order.save(update_fields=["status", "updated_at"])
        _notify(job, "Order packed", f"{job.job_no} has been packed and is ready for delivery.")
    return JsonResponse({"packing": _packing(packing)})
