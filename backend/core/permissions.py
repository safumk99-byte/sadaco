from django.db.models import F, Q
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import Department, StaffRole


def active_staff_profile(user):
    if not user or not user.is_authenticated:
        return None
    try:
        profile = user.staff_profile
    except Exception:
        return None
    return profile if profile.employment_status == "active" else None


def is_founder(profile):
    if profile is None or profile.employment_status != "active":
        return False
    now = timezone.now()
    return StaffRole.objects.filter(
        staff=profile,
        role__code__in=["founder", "super_admin"],
        division__isnull=True,
        department__isnull=True,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()


def has_permission(profile, permission_code, *, division_id=None, department_id=None):
    """Evaluate a configured permission against active role and organizational scope.

    Missing permissions and out-of-scope assignments deny access. Active global
    Founder/Super Admin roles retain their documented cross-division override.
    """
    if (
        profile is None
        or profile.employment_status != "active"
        or not permission_code
    ):
        return False
    if is_founder(profile):
        return True

    if department_id and not division_id:
        division_id = Department.objects.filter(pk=department_id).values_list(
            "division_id", flat=True
        ).first()
        if division_id is None:
            return False
    elif department_id and not Department.objects.filter(
        pk=department_id, division_id=division_id
    ).exists():
        return False

    now = timezone.now()
    assignments = StaffRole.objects.filter(
        staff=profile,
        role__permissions__code=permission_code,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))

    if division_id is None:
        assignments = assignments.filter(
            division__isnull=True, department__isnull=True
        )
    elif department_id is None:
        assignments = assignments.filter(
            Q(division__isnull=True, department__isnull=True)
            | Q(division_id=division_id, department__isnull=True)
            | (
                Q(department__division_id=division_id)
                & (Q(division__isnull=True) | Q(division_id=division_id))
            )
        )
    else:
        assignments = assignments.filter(
            Q(division__isnull=True, department__isnull=True)
            | Q(division_id=division_id, department__isnull=True)
            | (
                Q(department_id=department_id)
                & (Q(division__isnull=True) | Q(division_id=division_id))
            )
        )
    return assignments.exists()


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
    now = timezone.now()
    assignments = StaffRole.objects.filter(
        staff=profile,
        role__code=role_code,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
    if division_id is not None:
        assignments = assignments.filter(
            Q(division__isnull=True, department__isnull=True)
            | Q(division_id=division_id, department__isnull=True)
            | (
                Q(department__division_id=division_id)
                & (Q(division__isnull=True) | Q(division_id=division_id))
            )
        )
    return assignments.exists()


def active_role_division_ids(profile, role_code):
    if profile is None or profile.employment_status != "active":
        return []
    now = timezone.now()
    assignments = StaffRole.objects.filter(
        staff=profile,
        role__code=role_code,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))

    division_ids = set(
        assignments.filter(
            division__isnull=False,
            department__isnull=True,
        ).values_list("division_id", flat=True)
    )
    division_ids.update(
        assignments.filter(
            division__isnull=True,
            department__isnull=False,
        ).values_list("department__division_id", flat=True)
    )
    division_ids.update(
        assignments.filter(
            division__isnull=False,
            department__isnull=False,
            division_id=F("department__division_id"),
        ).values_list("division_id", flat=True)
    )
    return sorted(division_ids)



def permission_scope_division_ids(profile, permission_code):
    """Return divisions covered by an active configured grant; None means global scope."""
    if profile is None or profile.employment_status != "active" or not permission_code:
        return []
    if is_founder(profile):
        return None
    now = timezone.now()
    assignments = StaffRole.objects.filter(
        staff=profile,
        role__permissions__code=permission_code,
        valid_from__lte=now,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now))
    if assignments.filter(division__isnull=True, department__isnull=True).exists():
        return None
    division_ids = set(
        assignments.filter(division__isnull=False).values_list("division_id", flat=True)
    )
    division_ids.update(
        assignments.filter(department__isnull=False).values_list(
            "department__division_id", flat=True
        )
    )
    return sorted(division_ids)


class HasConfiguredRolePermission(BasePermission):
    """Fail-closed DRF permission backed by RolePermission and StaffRole scope."""

    message = "Your active role does not grant this action."

    def _permission_code(self, view):
        return getattr(view, "permission_codes", {}).get(getattr(view, "action", None))

    def has_permission(self, request, view):
        profile = active_staff_profile(request.user)
        code = self._permission_code(view)
        if profile is None or not code:
            return False
        if is_founder(profile):
            return True
        now = timezone.now()
        return StaffRole.objects.filter(
            staff=profile,
            role__permissions__code=code,
            valid_from__lte=now,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()

    def has_object_permission(self, request, view, obj):
        profile = active_staff_profile(request.user)
        code = self._permission_code(view)
        if profile is None or not code:
            return False
        if is_founder(profile):
            return True
        division_id = getattr(obj, "division_id", None)
        if division_id is None and hasattr(obj, "enquiry"):
            division_id = obj.enquiry.division_id
        if division_id is None and hasattr(obj, "orders"):
            return False
        return bool(division_id and has_permission(
            profile, code, division_id=division_id
        ))
