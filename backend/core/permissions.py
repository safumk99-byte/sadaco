from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import StaffRole


class IsFounderOrScopedDivisionMember(BasePermission):
    """Require an active staff profile and enforce division-scoped access."""

    message = "You do not have access to this division."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return hasattr(user, "staff_profile") and user.staff_profile.employment_status == "active"

    def has_object_permission(self, request, view, obj):
        profile = request.user.staff_profile
        active_roles = StaffRole.objects.filter(
            staff=profile,
            role__code__in=["founder", "super_admin"],
            valid_from__lte=__import__("django.utils.timezone", fromlist=["now"]).now(),
        ).filter(
            __import__("django.db.models", fromlist=["Q"]).Q(valid_until__isnull=True)
            | __import__("django.db.models", fromlist=["Q"]).Q(valid_until__gt=__import__("django.utils.timezone", fromlist=["now"]).now())
        )
        if active_roles.exists():
            return True

        division_id = getattr(obj, "division_id", None)
        if division_id is None and hasattr(obj, "enquiry"):
            division_id = obj.enquiry.division_id
        if division_id is None:
            return False
        return profile.divisions.filter(pk=division_id).exists()
