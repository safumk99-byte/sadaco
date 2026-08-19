from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Notification, UserProfile
from sales.models import SalesOrder, DesignApproval
from .forms import ProductionJobForm, ProductionProgressForm, ProductionMaterialForm, ProductionIssueForm
from .models import ProductionJob, ProductionProgress, ProductionMaterial, ProductionIssue

manager_required = role_required("super_admin", "institution_admin", "manager")


def _is_staff(user):
    return hasattr(user, "staff_profile") and user.staff_profile is not None


def _job_visible(user, job):
    if user.is_superuser or getattr(getattr(user, "profile", None), "role", None) in ("super_admin", "institution_admin", "manager"):
        return True
    return _is_staff(user) and job.assigned_staff_id == user.staff_profile.id


def _notify_job(job, title, message):
    recipients = []
    if job.assigned_staff and job.assigned_staff.user_id:
        recipients.append(job.assigned_staff.user)
    if job.created_by_id:
        recipients.append(job.created_by)
    recipients.extend(UserProfile.objects.filter(role__in=[UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER], is_active=True).values_list("user", flat=True))
    seen=set()
    for user_id in recipients:
        uid=getattr(user_id, "pk", user_id)
        if uid in seen: continue
        seen.add(uid)
        Notification.objects.create(user_id=uid, notification_type=Notification.Type.TASK, priority=Notification.Priority.NORMAL, title=title, message=message, url=f"/production/jobs/{job.pk}/")

@login_required
@manager_required
def dashboard(request):
    jobs = ProductionJob.objects.select_related("order", "assigned_staff__user")
    context = {
        "title":"Production Management",
        "jobs":jobs[:20],
        "total":jobs.count(),
        "pending":jobs.filter(status__in=[ProductionJob.Status.PENDING, ProductionJob.Status.ASSIGNED]).count(),
        "active":jobs.filter(status=ProductionJob.Status.IN_PROGRESS).count(),
        "on_hold":jobs.filter(status=ProductionJob.Status.ON_HOLD).count(),
        "completed":jobs.filter(status=ProductionJob.Status.COMPLETED).count(),
        "delayed":jobs.filter(deadline__lt=timezone.localdate()).exclude(status__in=[ProductionJob.Status.COMPLETED, ProductionJob.Status.CANCELLED]).count(),
    }
    return render(request,"production/dashboard.html",context)

@login_required
def job_list(request):
    qs=ProductionJob.objects.select_related("order","assigned_staff__user")
    if not (request.user.is_superuser or getattr(getattr(request.user,"profile",None),"role",None) in ("super_admin","institution_admin","manager")):
        if _is_staff(request.user): qs=qs.filter(assigned_staff=request.user.staff_profile)
        else: qs=qs.none()
    q=request.GET.get("q","").strip(); status=request.GET.get("status",""); station=request.GET.get("station","")
    if q: qs=qs.filter(Q(job_no__icontains=q)|Q(order__order_no__icontains=q)|Q(order__customer__name__icontains=q)|Q(order__item_description__icontains=q))
    if status: qs=qs.filter(status=status)
    if station: qs=qs.filter(station=station)
    return render(request,"production/job_list.html",{"title":"Production Jobs","jobs":qs,"query":q,"selected_status":status,"selected_station":station,"statuses":ProductionJob.Status.choices,"stations":ProductionJob.Station.choices})

@login_required
@manager_required
def job_create(request, order_pk):
    order=get_object_or_404(SalesOrder.objects.select_related("customer"),pk=order_pk)
    if order.status not in (SalesOrder.Status.PRODUCTION_PENDING, SalesOrder.Status.CONFIRMED):
        messages.error(request,"This order is not ready for production planning.")
        return redirect("sales:order_detail",pk=order.pk)
    latest_design=order.quotation.designs.filter(status=DesignApproval.Status.APPROVED).first() if order.quotation_id else None
    if not latest_design:
        messages.error(request,"Production can start only after customer design approval.")
        return redirect("sales:order_detail",pk=order.pk)
    if ProductionJob.objects.filter(order=order,status__in=[ProductionJob.Status.PENDING,ProductionJob.Status.ASSIGNED,ProductionJob.Status.IN_PROGRESS,ProductionJob.Status.ON_HOLD]).exists():
        messages.info(request,"An active production job already exists for this order.")
        return redirect("production:job_list")
    form=ProductionJobForm(request.POST or None,initial={"deadline":order.deadline,"assigned_staff":order.responsible_staff,"status":ProductionJob.Status.PENDING})
    if request.method=="POST" and form.is_valid():
        job=form.save(commit=False); job.order=order; job.created_by=request.user; job.save()
        order.status=SalesOrder.Status.PRODUCTION_PENDING; order.save(update_fields=["status","updated_at"])
        _notify_job(job,"Production job created",f"{job.job_no} was created for {order.order_no}.")
        messages.success(request,f"Production job {job.job_no} created.")
        return redirect("production:job_detail",pk=job.pk)
    return render(request,"production/job_form.html",{"title":f"Plan Production · {order.order_no}","form":form,"order":order})

@login_required
def job_detail(request,pk):
    job=get_object_or_404(ProductionJob.objects.select_related("order__customer","order__quotation","assigned_staff__user","created_by").prefetch_related("progress_updates","materials","issues"),pk=pk)
    if not _job_visible(request.user,job):
        from django.core.exceptions import PermissionDenied; raise PermissionDenied
    role=getattr(getattr(request.user,"profile",None),"role",None)
    can_manage=request.user.is_superuser or role in ("super_admin","institution_admin","manager")
    return render(request,"production/job_detail.html",{"title":job.job_no,"job":job,"progress_form":ProductionProgressForm(),"material_form":ProductionMaterialForm(),"issue_form":ProductionIssueForm(),"stage_choices":ProductionJob.Stage.choices,"can_manage":can_manage})

@login_required
def job_update(request,pk):
    job=get_object_or_404(ProductionJob,pk=pk)
    if not _job_visible(request.user,job):
        from django.core.exceptions import PermissionDenied; raise PermissionDenied
    form=ProductionJobForm(request.POST or None,instance=job)
    if request.method=="POST" and form.is_valid():
        old=job.status; job=form.save();
        if job.status!=old: _notify_job(job,"Production status updated",f"{job.job_no}: {job.get_status_display()}.")
        messages.success(request,"Production job updated.")
        return redirect("production:job_detail",pk=pk)
    return render(request,"production/job_form.html",{"title":f"Edit {job.job_no}","form":form,"order":job.order,"job":job})

@login_required
def progress_add(request,pk):
    job=get_object_or_404(ProductionJob,pk=pk)
    if not _job_visible(request.user,job):
        from django.core.exceptions import PermissionDenied; raise PermissionDenied
    form=ProductionProgressForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        update=form.save(commit=False); update.job=job; update.updated_by=request.user; update.save()
        job.stage=update.stage; job.progress_percent=update.progress_percent
        if update.progress_percent>=100: job.status=ProductionJob.Status.COMPLETED
        elif job.status in (ProductionJob.Status.PENDING,ProductionJob.Status.ASSIGNED,ProductionJob.Status.ON_HOLD): job.status=ProductionJob.Status.IN_PROGRESS
        job.save()
        if update.progress_percent > 0 and job.order.status != SalesOrder.Status.IN_PRODUCTION:
            job.order.status=SalesOrder.Status.IN_PRODUCTION
            job.order.save(update_fields=["status","updated_at"])
        _notify_job(job,"Production progress updated",f"{job.job_no} is {job.progress_percent}% complete.")
        messages.success(request,"Progress update saved.")
    return redirect("production:job_detail",pk=pk)

@login_required
@manager_required
def material_add(request,pk):
    job=get_object_or_404(ProductionJob,pk=pk); form=ProductionMaterialForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False); item.job=job; item.save(); messages.success(request,"Material requirement added.")
    return redirect("production:job_detail",pk=pk)

@login_required
def issue_add(request,pk):
    job=get_object_or_404(ProductionJob,pk=pk)
    if not _job_visible(request.user,job):
        from django.core.exceptions import PermissionDenied; raise PermissionDenied
    form=ProductionIssueForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        issue=form.save(commit=False); issue.job=job; issue.created_by=request.user; issue.save()
        if issue.issue_type==ProductionIssue.Type.DELAY: job.status=ProductionJob.Status.ON_HOLD; job.save(update_fields=["status","updated_at"])
        _notify_job(job,f"Production {issue.get_issue_type_display()}",f"{job.job_no}: {issue.reason[:140]}")
        messages.success(request,f"{issue.get_issue_type_display()} recorded.")
    return redirect("production:job_detail",pk=pk)
