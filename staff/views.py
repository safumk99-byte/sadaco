from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg, Count, Q

from .decorators import staff_manager_required
from .forms import (
    AttendanceForm,
    DesignationForm,
    PerformanceForm,
    StaffCreateForm,
    StaffEditForm,
    TaskForm,
    WorkAreaForm,
)
from .models import Designation, PerformanceRecord, StaffAttendance, StaffProfile, StaffTask, WorkArea
from .services import (
    attendance_queryset_for_user,
    can_manage_staff,
    dashboard_stats,
    performance_queryset_for_user,
    staff_for_user,
    task_queryset_for_user,
)


@login_required
def staff_list(request):
    qs = staff_for_user(request.user)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    designation = request.GET.get("designation", "").strip()
    work_area = request.GET.get("work_area", "").strip()
    if query:
        qs = qs.filter(
            user__first_name__icontains=query
        ) | staff_for_user(request.user).filter(
            user__last_name__icontains=query
        ) | staff_for_user(request.user).filter(
            staff_id__icontains=query
        )
    if status:
        qs = qs.filter(status=status)
    if designation:
        qs = qs.filter(designation_id=designation)
    if work_area:
        qs = qs.filter(work_area_id=work_area)
    return render(
        request,
        "staff/staff_list.html",
        {"title": "Staff Management", "staff_members": qs.distinct(), "stats": dashboard_stats(request.user), "query": query,
         "can_manage": can_manage_staff(request.user), "status": status, "designation": designation, "work_area": work_area, "designations": Designation.objects.filter(is_active=True), "work_areas": WorkArea.objects.filter(is_active=True)},
    )


@staff_manager_required
def staff_create(request):
    form = StaffCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Staff member created successfully.")
        return redirect("staff:list")
    return render(request, "staff/staff_form.html", {"title": "Add Staff", "form": form})


@staff_manager_required
def staff_edit(request, pk):
    profile = get_object_or_404(staff_for_user(request.user), pk=pk)
    form = StaffEditForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Staff member updated successfully.")
        return redirect("staff:detail", pk=pk)
    return render(request, "staff/staff_form.html", {"title": "Edit Staff", "form": form, "editing": True, "staff_member": profile})


@login_required
def staff_detail(request, pk):
    profile = get_object_or_404(staff_for_user(request.user), pk=pk)
    tasks = profile.tasks.order_by("-created_at")[:8]
    attendance = profile.attendance.order_by("-date")[:8]
    performance = profile.performance_records.order_by("-review_date")[:5]
    task_total = profile.tasks.count()
    task_completed = profile.tasks.filter(status=StaffTask.Status.COMPLETED).count()
    task_rate = round((task_completed / task_total) * 100) if task_total else 0
    attendance_total = profile.attendance.count()
    attendance_present = profile.attendance.filter(status=StaffAttendance.Status.PRESENT).count()
    attendance_rate = round((attendance_present / attendance_total) * 100) if attendance_total else 0
    avg_score = profile.performance_records.aggregate(value=Avg("score"))["value"] or 0
    kpi_score = round((task_rate * 0.4) + (attendance_rate * 0.3) + (float(avg_score) * 0.3)) if (task_total or attendance_total or avg_score) else 0
    return render(
        request,
        "staff/staff_detail.html",
        {
            "title": "Staff Profile",
            "staff_member": profile,
            "tasks": tasks,
            "attendance": attendance,
            "performance": performance,
            "kpi": {
                "task_rate": task_rate,
                "attendance_rate": attendance_rate,
                "average_review": round(float(avg_score), 1),
                "score": min(kpi_score, 100),
            },
        },
    )


@staff_manager_required
def designation_list(request):
    return render(request, "staff/designations.html", {"title": "Designations", "items": Designation.objects.all()})


@staff_manager_required
def designation_create(request):
    form = DesignationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Designation saved.")
        return redirect("staff:designations")
    return render(request, "staff/simple_form.html", {"title": "Add Designation", "form": form, "back_url": "staff:designations"})


@staff_manager_required
def designation_edit(request, pk):
    item = get_object_or_404(Designation, pk=pk)
    form = DesignationForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Designation updated.")
        return redirect("staff:designations")
    return render(request, "staff/simple_form.html", {"title": "Edit Designation", "form": form, "back_url": "staff:designations"})


@staff_manager_required
def work_area_list(request):
    return render(request, "staff/work_areas.html", {"title": "Work Areas", "items": WorkArea.objects.all()})


@staff_manager_required
def work_area_create(request):
    form = WorkAreaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Work area saved.")
        return redirect("staff:work_areas")
    return render(request, "staff/simple_form.html", {"title": "Add Work Area", "form": form, "back_url": "staff:work_areas"})


@staff_manager_required
def work_area_edit(request, pk):
    item = get_object_or_404(WorkArea, pk=pk)
    form = WorkAreaForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Work area updated.")
        return redirect("staff:work_areas")
    return render(request, "staff/simple_form.html", {"title": "Edit Work Area", "form": form, "back_url": "staff:work_areas"})


@login_required
def task_list(request):
    tasks = task_queryset_for_user(request.user)
    return render(request, "staff/tasks.html", {"title": "Staff Tasks", "tasks": tasks, "can_manage": can_manage_staff(request.user)})


@staff_manager_required
def task_create(request):
    form = TaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.assigned_by = request.user
        if task.status == StaffTask.Status.COMPLETED:
            from django.utils import timezone
            task.completed_at = timezone.now()
        else:
            task.completed_at = None
        task.save()
        messages.success(request, "Task created successfully.")
        return redirect("staff:tasks")
    return render(request, "staff/simple_form.html", {"title": "Create Task", "form": form, "back_url": "staff:tasks"})


@staff_manager_required
def task_edit(request, pk):
    task = get_object_or_404(StaffTask, pk=pk)
    form = TaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.assigned_by = task.assigned_by or request.user
        if task.status == StaffTask.Status.COMPLETED and not task.completed_at:
            task.completed_at = __import__("django.utils.timezone", fromlist=["timezone"]).timezone.now()
        elif task.status != StaffTask.Status.COMPLETED:
            task.completed_at = None
        task.save()
        messages.success(request, "Task updated.")
        return redirect("staff:tasks")
    return render(request, "staff/simple_form.html", {"title": "Edit Task", "form": form, "back_url": "staff:tasks"})


@login_required
def attendance_list(request):
    records = attendance_queryset_for_user(request.user)
    return render(request, "staff/attendance.html", {"title": "Staff Attendance", "records": records, "can_manage": can_manage_staff(request.user)})


@staff_manager_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.marked_by = request.user
        record.save()
        messages.success(request, "Attendance saved.")
        return redirect("staff:attendance")
    return render(request, "staff/simple_form.html", {"title": "Mark Attendance", "form": form, "back_url": "staff:attendance"})


@login_required
def performance_list(request):
    records = performance_queryset_for_user(request.user)
    kpi_rows = []
    visible_staff = staff_for_user(request.user)
    for profile in visible_staff:
        task_total = profile.tasks.count()
        task_completed = profile.tasks.filter(status=StaffTask.Status.COMPLETED).count()
        task_rate = round((task_completed / task_total) * 100) if task_total else 0
        att_total = profile.attendance.count()
        att_present = profile.attendance.filter(status=StaffAttendance.Status.PRESENT).count()
        attendance_rate = round((att_present / att_total) * 100) if att_total else 0
        avg_score = profile.performance_records.aggregate(value=Avg("score"))["value"] or 0
        score = round((task_rate * 0.4) + (attendance_rate * 0.3) + (float(avg_score) * 0.3)) if (task_total or att_total or avg_score) else 0
        kpi_rows.append({
            "staff": profile,
            "task_rate": task_rate,
            "attendance_rate": attendance_rate,
            "average_review": round(float(avg_score), 1),
            "score": min(score, 100),
        })
    return render(request, "staff/performance.html", {
        "title": "Staff Performance",
        "records": records,
        "kpi_rows": kpi_rows,
        "can_manage": can_manage_staff(request.user),
    })


@staff_manager_required
def performance_create(request):
    form = PerformanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.evaluator = request.user
        record.save()
        messages.success(request, "Performance record saved.")
        return redirect("staff:performance")
    return render(request, "staff/simple_form.html", {"title": "Add Performance Record", "form": form, "back_url": "staff:performance"})
