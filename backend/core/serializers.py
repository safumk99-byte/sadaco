from rest_framework import serializers

from .models import Customer, DesignApproval, DesignRevision, Enquiry, FollowUp
from .models import staff_has_division_membership
from .permissions import active_staff_profile, is_founder


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "customer_code", "display_name", "mobile", "whatsapp_mobile",
            "email", "address", "location", "customer_type", "notes", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "completed_at", "created_at", "updated_at"]


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            "id", "enquiry_number", "customer", "division", "enquiry_date", "source",
            "requested_product_service", "assigned_to", "follow_up_at", "status",
            "notes", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "status"]

    def validate(self, attrs):
        profile = active_staff_profile(self.context["request"].user)
        division = attrs.get("division", getattr(self.instance, "division", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if division and not is_founder(profile) and not profile.divisions.filter(pk=division.pk).exists():
            raise serializers.ValidationError({"division": "You are not assigned to this division."})
        assigned_to = attrs.get("assigned_to", getattr(self.instance, "assigned_to", None))
        if assigned_to and division and not staff_has_division_membership(assigned_to.pk, division.pk):
            raise serializers.ValidationError({"assigned_to": "Assignee must belong to the enquiry division."})
        if customer and division:
            if self.instance and (
                self.instance.customer_id != customer.id or self.instance.division_id != division.id
            ):
                raise serializers.ValidationError("Customer and division cannot be changed after enquiry creation.")
        return attrs


class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = ["id", "enquiry", "assigned_to", "due_at", "status", "note", "completed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "completed_at", "created_at", "updated_at"]

    def validate(self, attrs):
        profile = active_staff_profile(self.context["request"].user)
        enquiry = attrs.get("enquiry", getattr(self.instance, "enquiry", None))
        if enquiry and not is_founder(profile) and not profile.divisions.filter(pk=enquiry.division_id).exists():
            raise serializers.ValidationError({"enquiry": "You do not have access to this enquiry's division."})
        assigned_to = attrs.get("assigned_to", getattr(self.instance, "assigned_to", None))
        if assigned_to and enquiry and not staff_has_division_membership(assigned_to.pk, enquiry.division_id):
            raise serializers.ValidationError({"assigned_to": "Assignee must belong to the enquiry division."})
        if self.instance and enquiry and self.instance.enquiry_id != enquiry.id:
            raise serializers.ValidationError({"enquiry": "A follow-up cannot be moved to another enquiry."})
        return attrs



class DesignApprovalReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignApproval
        fields = ["id", "reviewer_type", "decision", "reviewed_by", "reviewed_at", "comments"]
        read_only_fields = fields


class DesignApprovalSubmissionSerializer(serializers.Serializer):
    reviewer_type = serializers.ChoiceField(choices=["customer", "manager"])
    decision = serializers.ChoiceField(choices=["approved", "revision_required"])
    comments = serializers.CharField(required=False, allow_blank=True, max_length=10000)


class DesignRevisionSerializer(serializers.ModelSerializer):
    approvals = DesignApprovalReadSerializer(many=True, read_only=True)

    class Meta:
        model = DesignRevision
        fields = [
            "id", "design_record", "revision_number", "status", "dimensions",
            "change_summary", "submitted_at", "locked_at", "created_by",
            "approvals", "created_at", "updated_at",
        ]
        read_only_fields = fields
