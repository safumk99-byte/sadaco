from rest_framework import serializers

from .models import Customer, Enquiry, FollowUp


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "customer_code", "display_name", "mobile", "whatsapp_mobile",
            "email", "address", "location", "customer_type", "notes", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            "id", "enquiry_number", "customer", "division", "enquiry_date", "source",
            "requested_product_service", "assigned_to", "follow_up_at", "status",
            "notes", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context["request"]
        profile = request.user.staff_profile
        division = attrs.get("division", getattr(self.instance, "division", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if division and not profile.role_assignments.filter(
            role__code__in=["founder", "super_admin"],
            division__isnull=True,
            valid_until__isnull=True,
        ).exists() and not profile.divisions.filter(pk=division.pk).exists():
            raise serializers.ValidationError({"division": "You are not assigned to this division."})
        if self.instance and customer and division:
            if self.instance.customer_id != customer.id or self.instance.division_id != division.id:
                raise serializers.ValidationError("Customer and division cannot be changed after enquiry creation.")
        return attrs


class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = ["id", "enquiry", "assigned_to", "due_at", "status", "note", "completed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_enquiry(self, enquiry):
        profile = self.context["request"].user.staff_profile
        is_founder = profile.role_assignments.filter(
            role__code__in=["founder", "super_admin"], division__isnull=True, valid_until__isnull=True
        ).exists()
        if not is_founder and not profile.divisions.filter(pk=enquiry.division_id).exists():
            raise serializers.ValidationError("You do not have access to this enquiry's division.")
        return enquiry
