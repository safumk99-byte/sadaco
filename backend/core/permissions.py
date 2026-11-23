from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import StaffRole


class IsFounderOrScopedDivisionMember(BasePermission):
    message = "You do not have access to this division."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        try:
            return user.staff_profile.employment_status == "active"
        except Exception:
            return False

    def has_object_permission(self, request, view, obj):
        profile = request.user.staff_profile
        now = timezone.now()
        is_founder = StaffRole.objects.filter(
            staff=profile, role__code__in=["founder", "super_admin"], valid_from__lte=now
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()
        if is_founder:
            return True
        division_id = getattr(obj, "division_id", None)
        if division_id is None and hasattr(obj, "enquiry"):
            division_id = obj.enquiry.division_id
        return bool(division_id and profile.divisions.filter(pk=division_id).exists())
