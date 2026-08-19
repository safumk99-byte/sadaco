
from .models import StaffAttendance, StaffProfile, StaffTask, PerformanceRecord
from django.utils import timezone


def staff_queryset():
    return StaffProfile.objects.select_related("user", "designation", "work_area")


def dashboard_stats(user=None):
    if user is not None and not can_manage_staff(user):
        own = StaffProfile.objects.filter(user=user)
        return {
            "total_staff": own.count(),
            "active_staff": own.filter(status=StaffProfile.Status.ACTIVE).count(),
            "inactive_staff": own.filter(status=StaffProfile.Status.INACTIVE).count(),
            "on_leave_staff": own.filter(status=StaffProfile.Status.ON_LEAVE).count(),
            "open_tasks": StaffTask.objects.filter(assigned_to__user=user).exclude(
                status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
            ).count(),
            "today_present": StaffAttendance.objects.filter(
                staff__user=user,
                date=timezone.localdate(),
                status=StaffAttendance.Status.PRESENT,
            ).count(),
        }

    return {
        "total_staff": StaffProfile.objects.count(),
        "active_staff": StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).count(),
        "inactive_staff": StaffProfile.objects.filter(status=StaffProfile.Status.INACTIVE).count(),
        "on_leave_staff": StaffProfile.objects.filter(status=StaffProfile.Status.ON_LEAVE).count(),
        "open_tasks": StaffTask.objects.exclude(
            status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
        ).count(),
        "today_present": StaffAttendance.objects.filter(
            date=timezone.localdate(),
            status=StaffAttendance.Status.PRESENT,
        ).count(),
    }


def staff_for_user(user):
    qs = staff_queryset()
    profile = getattr(user, "profile", None)
    if user.is_superuser or (
        profile and profile.role in {"super_admin", "institution_admin", "manager"}
    ):
        return qs
    return qs.filter(user=user)


def can_manage_staff(user):
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role in {"super_admin", "institution_admin", "manager"})


def task_queryset_for_user(user):
    qs = StaffTask.objects.select_related("assigned_to__user", "assigned_by")
    if can_manage_staff(user):
        return qs
    return qs.filter(assigned_to__user=user)


def attendance_queryset_for_user(user):
    qs = StaffAttendance.objects.select_related("staff__user", "marked_by")
    if can_manage_staff(user):
        return qs
    return qs.filter(staff__user=user)


def performance_queryset_for_user(user):
    qs = PerformanceRecord.objects.select_related("staff__user", "evaluator")
    if can_manage_staff(user):
        return qs
    return qs.filter(staff__user=user)
