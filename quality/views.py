from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Notification, UserProfile
from production.models import ProductionJob
from sales.models import SalesOrder
from staff.models import StaffProfile
from .forms import QualityCheckForm, ReworkRecordForm, PackingRecordForm
from .models import QualityCheck, ReworkRecord, PackingRecord

manager_required = role_required("super_admin", "institution_admin", "manager")


def _is_manager(user):
    return user.is_superuser or getattr(getattr(user, "profile", None), "role", None) in (
        "super_admin", "institution_admin", "manager"
    )


def _visible_job(user, job):
    if _is_manager(user):
        return True
    return hasattr(user, "staff_profile") and job.assigned_staff_id == user.staff_profile.id


def _notify(job, title, message, priority=Notification.Priority.NORMAL):
    users = []
    if job.assigned_staff_id:
        users.append(job.assigned_staff.user)
    if job.created_by_id:
        users.append(job.created_by)
    users += list(UserProfile.objects.filter(
        role__in=[
            UserProfile.Role.SUPER_ADMIN,
            UserProfile.Role.INSTITUTION_ADMIN,
            UserProfile.Role.MANAGER,
        ],
        is_active=True,
    ).values_list("user", flat=True))

    seen = set()
    for item in users:
        uid = getattr(item, "pk", item)
        if uid in seen:
            continue
        seen.add(uid)
        Notification.objects.create(
            user_id=uid,
            notification_type=Notification.Type.TASK,
            priority=priority,
            title=title,
            message=message,
            url=f"/quality/jobs/{job.pk}/",
        )


def _sync_job(job):
    latest_final = job.quality_checks.filter(
        check_type=QualityCheck.CheckType.FINAL
    ).first()
    open_rework = job.rework_records.exclude(
        status=ReworkRecord.Status.COMPLETED
    ).exclude(status=ReworkRecord.Status.CANCELLED).exists()

    if open_rework or (latest_final and latest_final.result in (
        QualityCheck.Result.FAIL, QualityCheck.Result.REWORK
    )):
        job.status = ProductionJob.Status.ON_HOLD
        job.stage = ProductionJob.Stage.QC_PENDING
        job.save(update_fields=["status", "stage", "updated_at"])
        if job.order.status != SalesOrder.Status.IN_PRODUCTION:
            job.order.status = SalesOrder.Status.IN_PRODUCTION
            job.order.save(update_fields=["status", "updated_at"])
        return

    if latest_final and latest_final.result == QualityCheck.Result.PASS:
        job.stage = ProductionJob.Stage.COMPLETED
        job.status = ProductionJob.Status.COMPLETED
        job.progress_percent = 100
        job.save(update_fields=["stage", "status", "progress_percent", "updated_at"])
        if job.order.status != SalesOrder.Status.READY:
            job.order.status = SalesOrder.Status.READY
            order_updates = ["status", "updated_at"]
            job.order.save(update_fields=order_updates)
        PackingRecord.objects.get_or_create(job=job)
        return

    job.stage = ProductionJob.Stage.QC_PENDING
    job.save(update_fields=["stage", "updated_at"])


@login_required
@manager_required
def dashboard(request):
    checks = QualityCheck.objects.select_related("job__order__customer", "inspector__user")
    jobs = ProductionJob.objects.filter(
        status__in=[ProductionJob.Status.COMPLETED, ProductionJob.Status.ON_HOLD]
    ).select_related("order__customer", "assigned_staff__user")

    q = request.GET.get("q", "").strip()
    result = request.GET.get("result", "").strip()
    if q:
        checks = checks.filter(
            Q(job__job_no__icontains=q)
            | Q(job__order__order_no__icontains=q)
            | Q(job__order__customer__name__icontains=q)
        )
    if result:
        checks = checks.filter(result=result)

    context = {
        "title": "Quality Control",
        "checks": checks[:50],
        "jobs": jobs[:20],
        "query": q,
        "selected_result": result,
        "result_choices": QualityCheck.Result.choices,
        "pending": ProductionJob.objects.filter(stage=ProductionJob.Stage.QC_PENDING).exclude(
            status=ProductionJob.Status.CANCELLED
        ).count(),
        "passed": QualityCheck.objects.filter(result=QualityCheck.Result.PASS).count(),
        "rework": ReworkRecord.objects.filter(
            status__in=[ReworkRecord.Status.OPEN, ReworkRecord.Status.IN_PROGRESS]
        ).count(),
        "packed": PackingRecord.objects.filter(status=PackingRecord.Status.PACKED).count(),
    }
    return render(request, "quality/dashboard.html", context)


@login_required
def job_detail(request, pk):
    job = get_object_or_404(
        ProductionJob.objects.select_related(
            "order__customer", "order__quotation", "assigned_staff__user"
        ).prefetch_related(
            "quality_checks__inspector__user", "rework_records__assigned_staff__user"
        ),
        pk=pk,
    )
    if not _visible_job(request.user, job):
        raise PermissionDenied

    return render(request, "quality/job_detail.html", {
        "title": f"QC · {job.job_no}",
        "job": job,
        "checks": job.quality_checks.all(),
        "reworks": job.rework_records.all(),
        "packing": getattr(job, "packing", None),
        "can_manage": _is_manager(request.user),
    })


@login_required
def quality_create(request, pk):
    job = get_object_or_404(ProductionJob, pk=pk)
    if not _visible_job(request.user, job):
        raise PermissionDenied

    form = QualityCheckForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
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
            _notify(
                job,
                "Quality issue recorded",
                f"{job.job_no}: {check.get_result_display()}.",
                Notification.Priority.HIGH,
            )
        elif check.result == QualityCheck.Result.PASS:
            _sync_job(job)
            _notify(job, "Quality check passed", f"{job.job_no} passed {check.get_check_type_display()}.")
        else:
            job.stage = ProductionJob.Stage.QC_PENDING
            job.save(update_fields=["stage", "updated_at"])

        messages.success(request, "Quality check saved.")
        return redirect("quality:job_detail", pk=job.pk)

    return render(request, "quality/check_form.html", {
        "title": f"New QC · {job.job_no}", "form": form, "job": job
    })


@login_required
def quality_update(request, pk):
    check = get_object_or_404(QualityCheck.objects.select_related("job"), pk=pk)
    if not _visible_job(request.user, check.job):
        raise PermissionDenied

    old = check.result
    form = QualityCheckForm(request.POST or None, instance=check)
    if request.method == "POST" and form.is_valid():
        check = form.save()
        _sync_job(check.job)
        if check.result != old:
            _notify(
                check.job,
                "Quality result updated",
                f"{check.job.job_no}: {check.get_result_display()}.",
                Notification.Priority.HIGH if check.result != QualityCheck.Result.PASS else Notification.Priority.NORMAL,
            )
        messages.success(request, "Quality check updated.")
        return redirect("quality:job_detail", pk=check.job.pk)

    return render(request, "quality/check_form.html", {
        "title": f"Edit QC · {check.job.job_no}", "form": form, "job": check.job, "check": check
    })


@login_required
def rework_create(request, pk):
    check = get_object_or_404(QualityCheck.objects.select_related("job"), pk=pk)
    if not _visible_job(request.user, check.job):
        raise PermissionDenied

    form = ReworkRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
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
        _notify(job, "Rework assigned", f"{job.job_no}: {rework.reason[:140]}", Notification.Priority.HIGH)

        messages.success(request, "Rework record created.")
        return redirect("quality:job_detail", pk=job.pk)

    return render(request, "quality/rework_form.html", {
        "title": f"Create Rework · {check.job.job_no}", "form": form, "job": check.job, "check": check
    })


@login_required
def rework_update(request, pk):
    rework = get_object_or_404(ReworkRecord.objects.select_related("job"), pk=pk)
    if not _visible_job(request.user, rework.job):
        raise PermissionDenied

    old = rework.status
    form = ReworkRecordForm(request.POST or None, instance=rework)
    if request.method == "POST" and form.is_valid():
        rework = form.save()
        if rework.status == ReworkRecord.Status.COMPLETED:
            rework.job.status = ProductionJob.Status.IN_PROGRESS
            rework.job.stage = ProductionJob.Stage.PRODUCTION
            rework.job.save(update_fields=["status", "stage", "updated_at"])
            _notify(rework.job, "Rework completed", f"{rework.job.job_no} rework was completed.")
        elif rework.status != old:
            _notify(rework.job, "Rework status updated", f"{rework.job.job_no}: {rework.get_status_display()}.")
        messages.success(request, "Rework updated.")
        return redirect("quality:job_detail", pk=rework.job.pk)

    return render(request, "quality/rework_form.html", {
        "title": f"Edit Rework · {rework.job.job_no}", "form": form, "job": rework.job, "rework": rework
    })


@login_required
def packing_update(request, pk):
    job = get_object_or_404(ProductionJob, pk=pk)
    if not _is_manager(request.user) and not _visible_job(request.user, job):
        raise PermissionDenied

    if job.status != ProductionJob.Status.COMPLETED:
        messages.error(request, "Packing is available only after final QC passes.")
        return redirect("quality:job_detail", pk=job.pk)

    packing, _ = PackingRecord.objects.get_or_create(job=job)
    form = PackingRecordForm(request.POST or None, instance=packing)
    if request.method == "POST" and form.is_valid():
        packing = form.save()
        if packing.status == PackingRecord.Status.PACKED:
            if not packing.fragile_protection or not packing.customer_label:
                messages.warning(request, "Packing saved, but fragile protection and customer label are not both confirmed.")
            _notify(job, "Order packed", f"{job.job_no} has been packed and is ready for delivery.")
            job.order.status = SalesOrder.Status.READY
            job.order.save(update_fields=["status", "updated_at"])
        messages.success(request, "Packing record saved.")
        return redirect("quality:job_detail", pk=job.pk)

    return render(request, "quality/packing_form.html", {
        "title": f"Packing · {job.job_no}", "form": form, "job": job, "packing": packing
    })
