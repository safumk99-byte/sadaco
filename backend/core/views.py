from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Customer, DesignRevision, Enquiry, FollowUp
from .permissions import IsActiveStaff, IsFounderOrScopedDivisionMember, active_role_division_ids, active_staff_profile, is_founder
from .serializers import (
    CustomerSerializer, DesignApprovalReadSerializer, DesignApprovalSubmissionSerializer,
    DesignRevisionSerializer, EnquirySerializer, FollowUpSerializer,
)
from .services import complete_follow_up, record_design_approval, transition_enquiry


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

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        enquiry = self.get_object()
        target = request.data.get("status")
        try:
            updated = transition_enquiry(
                enquiry_id=enquiry.pk,
                target_status=target,
                actor=request.user.staff_profile,
                reason=request.data.get("reason", ""),
            )
        except ValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages))
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)


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

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        follow_up = self.get_object()
        try:
            updated = complete_follow_up(
                follow_up_id=follow_up.pk,
                actor=request.user.staff_profile,
                note=request.data.get("note"),
            )
        except ValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages))
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)



class DesignRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DesignRevisionSerializer
    permission_classes = [IsActiveStaff]

    def get_queryset(self):
        profile = active_staff_profile(self.request.user)
        if profile is None:
            return DesignRevision.objects.none()
        queryset = DesignRevision.objects.select_related(
            "design_record", "design_record__sales_order", "created_by"
        ).prefetch_related("approvals")
        if not is_founder(profile):
            manager_division_ids = active_role_division_ids(profile, "manager")
            queryset = queryset.filter(
                Q(design_record__sales_order__division__in=profile.divisions.all())
                | Q(design_record__sales_order__division_id__in=manager_division_ids)
            ).distinct()
        return queryset

    @action(detail=True, methods=["post"], url_path="approval")
    def approval(self, request, pk=None):
        revision = self.get_object()
        input_serializer = DesignApprovalSubmissionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            approval = record_design_approval(
                revision_id=revision.pk,
                actor=request.user.staff_profile,
                **input_serializer.validated_data,
            )
        except ValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail)
        return Response(
            DesignApprovalReadSerializer(approval).data,
            status=status.HTTP_201_CREATED,
        )
