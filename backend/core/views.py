from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from rest_framework import viewsets

from .models import Customer, Enquiry, FollowUp
from .permissions import IsActiveStaff, IsFounderOrScopedDivisionMember, active_staff_profile, is_founder
from .serializers import CustomerSerializer, EnquirySerializer, FollowUpSerializer


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "sadaco-erp-api"})


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsActiveStaff]

    def get_queryset(self):
        profile = active_staff_profile(self.request.user)
        if profile is None:
            return Customer.objects.none()
        if is_founder(profile):
            return Customer.objects.all()
        division_ids = profile.divisions.values_list("id", flat=True)
        return Customer.objects.filter(
            Q(enquiries__division_id__in=division_ids) | Q(orders__division_id__in=division_ids)
        ).distinct()


class EnquiryViewSet(viewsets.ModelViewSet):
    serializer_class = EnquirySerializer
    permission_classes = [IsFounderOrScopedDivisionMember]

    def get_queryset(self):
        profile = active_staff_profile(self.request.user)
        if profile is None:
            return Enquiry.objects.none()
        qs = Enquiry.objects.select_related("customer", "division", "assigned_to", "created_by")
        if not is_founder(profile):
            qs = qs.filter(division__in=profile.divisions.all())
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.staff_profile)


class FollowUpViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpSerializer
    permission_classes = [IsActiveStaff]

    def get_queryset(self):
        profile = active_staff_profile(self.request.user)
        if profile is None:
            return FollowUp.objects.none()
        qs = FollowUp.objects.select_related("enquiry", "assigned_to")
        if not is_founder(profile):
            qs = qs.filter(enquiry__division__in=profile.divisions.all())
        return qs
