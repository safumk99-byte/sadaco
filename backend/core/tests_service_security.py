from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import (
    AuditEvent, Customer, Division, Enquiry, FollowUp,
    Role, StaffDivision, StaffProfile, StaffRole,
)
from .services import complete_follow_up, transition_enquiry


class CRMServiceAuthorizationTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(
            code="service-auth", name="Service Authorization"
        )
        self.other_division = Division.objects.create(
            code="service-auth-other", name="Service Authorization Other"
        )
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="service-auth-user", password="test-password-123"
        )
        self.other_user = user_model.objects.create_user(
            username="service-auth-other-user", password="test-password-123"
        )
        self.staff = StaffProfile.objects.create(
            user=self.user, display_name="Service Authorization Staff"
        )
        self.other_staff = StaffProfile.objects.create(
            user=self.other_user, display_name="Other Division Staff"
        )
        StaffDivision.objects.create(staff=self.staff, division=self.division)
        StaffDivision.objects.create(
            staff=self.other_staff, division=self.other_division
        )
        self.customer = Customer.objects.create(
            customer_code="SERVICE-AUTH-C1",
            display_name="Service Authorization Customer",
        )
        self.enquiry = Enquiry.objects.create(
            enquiry_number="SERVICE-AUTH-E1",
            customer=self.customer,
            division=self.division,
            source=Enquiry.Source.PHONE,
            requested_product_service="Test service",
            created_by=self.staff,
        )
        self.follow_up = FollowUp.objects.create(
            enquiry=self.enquiry,
            due_at=timezone.now(),
        )

    def test_transition_enquiry_rejects_actor_from_another_division(self):
        with self.assertRaises(ValidationError):
            transition_enquiry(
                enquiry_id=self.enquiry.pk,
                target_status=Enquiry.Status.CONTACTED,
                actor=self.other_staff,
            )

        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.NEW)
        self.assertFalse(AuditEvent.objects.exists())

    def test_complete_follow_up_rejects_actor_from_another_division(self):
        with self.assertRaises(ValidationError):
            complete_follow_up(
                follow_up_id=self.follow_up.pk,
                actor=self.other_staff,
            )

        self.follow_up.refresh_from_db()
        self.assertEqual(self.follow_up.status, FollowUp.Status.OPEN)
        self.assertFalse(AuditEvent.objects.exists())

    def test_transition_enquiry_rejects_inactive_actor_even_with_membership(self):
        self.staff.employment_status = StaffProfile.EmploymentStatus.INACTIVE
        self.staff.save(update_fields=["employment_status"])

        with self.assertRaises(ValidationError):
            transition_enquiry(
                enquiry_id=self.enquiry.pk,
                target_status=Enquiry.Status.CONTACTED,
                actor=self.staff,
            )

        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.NEW)
        self.assertFalse(AuditEvent.objects.exists())

    def test_complete_follow_up_rejects_inactive_actor_even_with_membership(self):
        self.staff.employment_status = StaffProfile.EmploymentStatus.INACTIVE
        self.staff.save(update_fields=["employment_status"])

        with self.assertRaises(ValidationError):
            complete_follow_up(
                follow_up_id=self.follow_up.pk,
                actor=self.staff,
            )

        self.follow_up.refresh_from_db()
        self.assertEqual(self.follow_up.status, FollowUp.Status.OPEN)
        self.assertFalse(AuditEvent.objects.exists())

    def test_global_founder_can_transition_without_division_membership(self):
        founder_user = get_user_model().objects.create_user(
            username="service-auth-founder", password="test-password-123"
        )
        founder = StaffProfile.objects.create(
            user=founder_user, display_name="Global Founder"
        )
        founder_role = Role.objects.create(
            code="founder", name="Founder"
        )
        StaffRole.objects.create(staff=founder, role=founder_role)

        updated = transition_enquiry(
            enquiry_id=self.enquiry.pk,
            target_status=Enquiry.Status.CONTACTED,
            actor=founder,
        )

        self.assertEqual(updated.status, Enquiry.Status.CONTACTED)
        event = AuditEvent.objects.get(entity_id=self.enquiry.pk)
        self.assertEqual(event.actor, founder)
