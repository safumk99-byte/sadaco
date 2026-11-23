from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Customer, Enquiry, FollowUp, StaffRole
from .permissions import IsFounderOrScopedDivisionMember
from .serializers import CustomerSerializer, EnquirySerializer, FollowUpSerializer


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "sadaco-erp-api"})


def _is_founder(profile):
    now = timezone.now()
    return StaffRole.objects.filter(
        staff=profile, role__code__in=["founder", "super_admin"], valid_from__lte=now
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gt=now)).exists()


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = self.request.user.staff_profile
        if _is_founder(profile):
            return Customer.objects.all()
        division_ids = profile.divisions.values_list("id", flat=True)
        return Customer.objects.filter(
            Q(enquiries__division_id__in=division_ids) | Q(orders__division_id__in=division_ids)
        ).distinct()


class EnquiryViewSet(viewsets.ModelViewSet):
    serializer_class = EnquirySerializer
    permission_classes = [IsFounderOrScopedDivisionMember]

    def get_queryset(self):
        profile = self.request.user.staff_profile
        qs = Enquiry.objects.select_related("customer", "division", "assigned_to", "created_by")
        if not _is_founder(profile):
            qs = qs.filter(division__in=profile.divisions.all())
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.staff_profile)


class FollowUpViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = self.request.user.staff_profile
        qs = FollowUp.objects.select_related("enquiry", "assigned_to")
        if not _is_founder(profile):
            qs = qs.filter(enquiry__division__in=profile.divisions.all())
        return qs
