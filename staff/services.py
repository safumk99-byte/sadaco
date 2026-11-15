from .models import StaffAttendance, StaffProfile, StaffTask, PerformanceRecord
from django.utils import timezone


def staff_queryset():
    return StaffProfile.objects.select_related("user", "designation", "work_area", "department")


def _role(user):
    if user.is_superuser:
        return "super_admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile and profile.is_active else None


def _is_global_admin(user):
    return _role(user) in {"super_admin", "institution_admin"}


def _department_id(user):
    profile = getattr(user, "profile", None)
    return profile.department_id if profile else None


def _department_staff_ids(user):
    department_id = _department_id(user)
    if not department_id:
        return StaffProfile.objects.none().values("pk")
    return StaffProfile.objects.filter(department_id=department_id).values("pk")


def staff_for_user(user):
    qs = staff_queryset()
    role = _role(user)
    if role in {"super_admin", "institution_admin"}:
        return qs
    if role == "manager":
        department_id = _department_id(user)
        if not department_id:
            return qs.none()
        return qs.filter(department_id=department_id)
    return qs.filter(user=user)


def can_manage_staff(user):
    return _role(user) in {"super_admin", "institution_admin", "manager"}


def dashboard_stats(user=None):
    today = timezone.localdate()
    if user is None:
        staff = StaffProfile.objects.all()
        tasks = StaffTask.objects.all()
        attendance = StaffAttendance.objects.all()
    elif _is_global_admin(user):
        staff = StaffProfile.objects.all()
        tasks = StaffTask.objects.all()
        attendance = StaffAttendance.objects.all()
    elif _role(user) == "manager":
        staff = staff_for_user(user)
        staff_ids = staff.values("pk")
        tasks = StaffTask.objects.filter(assigned_to_id__in=staff_ids)
        attendance = StaffAttendance.objects.filter(staff_id__in=staff_ids)
    else:
        staff = StaffProfile.objects.filter(user=user)
        tasks = StaffTask.objects.filter(assigned_to__user=user)
        attendance = StaffAttendance.objects.filter(staff__user=user)

    return {
        "total_staff": staff.count(),
        "active_staff": staff.filter(status=StaffProfile.Status.ACTIVE).count(),
        "inactive_staff": staff.filter(status=StaffProfile.Status.INACTIVE).count(),
        "on_leave_staff": staff.filter(status=StaffProfile.Status.ON_LEAVE).count(),
        "open_tasks": tasks.exclude(
            status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
        ).count(),
        "today_present": attendance.filter(
            date=today, status=StaffAttendance.Status.PRESENT
        ).count(),
    }


def task_queryset_for_user(user):
    qs = StaffTask.objects.select_related("assigned_to__user", "assigned_by", "assigned_to__department")
    if _is_global_admin(user):
        return qs
    if _role(user) == "manager":
        department_id = _department_id(user)
        return qs.filter(assigned_to__department_id=department_id) if department_id else qs.none()
    return qs.filter(assigned_to__user=user)


def attendance_queryset_for_user(user):
    qs = StaffAttendance.objects.select_related("staff__user", "marked_by", "staff__department")
    if _is_global_admin(user):
        return qs
    if _role(user) == "manager":
        department_id = _department_id(user)
        return qs.filter(staff__department_id=department_id) if department_id else qs.none()
    return qs.filter(staff__user=user)


def performance_queryset_for_user(user):
    qs = PerformanceRecord.objects.select_related("staff__user", "evaluator", "staff__department")
    if _is_global_admin(user):
        return qs
    if _role(user) == "manager":
        department_id = _department_id(user)
        return qs.filter(staff__department_id=department_id) if department_id else qs.none()
    return qs.filter(staff__user=user)
