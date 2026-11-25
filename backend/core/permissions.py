from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import StaffRole


def active_staff_profile(user):
    if not user or not user.is_authenticated:
        return None
    try:
        profile = user.staff_profile
    except Exception:
        return None
    return profile if profile.employment_status == "active" else None


def is_founder(profile):
    now = timezone.now()
    return StaffRole.objects.filter(
        staff=profile,
        role__code__in=["founder", "super_admin"],
        division__isnull=True,
        department__isnull=True,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()


class IsActiveStaff(BasePermission):
    message = "An active staff profile is required."

    def has_permission(self, request, view):
        return active_staff_profile(request.user) is not None


class IsFounderOrScopedDivisionMember(IsActiveStaff):
    message = "You do not have access to this division."

    def has_object_permission(self, request, view, obj):
        profile = active_staff_profile(request.user)
        if profile is None:
            return False
        if is_founder(profile):
            return True
        division_id = getattr(obj, "division_id", None)
        if division_id is None and hasattr(obj, "enquiry"):
            division_id = obj.enquiry.division_id
        return bool(division_id and profile.divisions.filter(pk=division_id).exists())


def has_active_role(profile, role_code, *, division_id=None):
    if profile is None or profile.employment_status != "active":
        return False
    assignments = StaffRole.objects.filter(
        staff=profile,
        role__code=role_code,
        valid_from__lte=timezone.now(),
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=timezone.now()))
    if division_id is not None:
        assignments = assignments.filter(Q(division__isnull=True) | Q(division_id=division_id))
    return assignments.exists()



def active_role_division_ids(profile, role_code):
    if profile is None or profile.employment_status != "active":
        return []
    now = timezone.now()
    return list(
        StaffRole.objects.filter(
            staff=profile,
            role__code=role_code,
            division__isnull=False,
            valid_from__lte=now,
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).values_list("division_id", flat=True)
    )
