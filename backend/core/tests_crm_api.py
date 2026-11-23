from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    AuditEvent,
    Customer,
    Division,
    Enquiry,
    FollowUp,
    StaffDivision,
    StaffProfile,
)


class CRMActionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.division = Division.objects.create(
            code="crm-actions", name="CRM Actions Division"
        )
        self.other_division = Division.objects.create(
            code="crm-other", name="CRM Other Division"
        )
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="crm-actions-user", password="test-password-123"
        )
        self.other_user = user_model.objects.create_user(
            username="crm-other-user", password="test-password-123"
        )
        self.staff = StaffProfile.objects.create(
            user=self.user, display_name="CRM Actions User"
        )
        self.other_staff = StaffProfile.objects.create(
            user=self.other_user, display_name="CRM Other User"
        )
        StaffDivision.objects.create(staff=self.staff, division=self.division)
        StaffDivision.objects.create(
            staff=self.other_staff, division=self.other_division
        )
        self.customer = Customer.objects.create(
            customer_code="CRM-ACTION-C1", display_name="CRM Action Customer"
        )
        self.enquiry = Enquiry.objects.create(
            enquiry_number="CRM-ACTION-E1",
            customer=self.customer,
            division=self.division,
            source=Enquiry.Source.PHONE,
            requested_product_service="Test service",
            created_by=self.staff,
        )
        self.follow_up = FollowUp.objects.create(
            enquiry=self.enquiry,
            due_at=timezone.now() + timezone.timedelta(days=1),
        )
        self.client.force_authenticate(self.user)

    def test_transition_endpoint_updates_status_and_audits(self):
        response = self.client.post(
            f"/api/enquiries/{self.enquiry.pk}/transition/",
            {"status": Enquiry.Status.CONTACTED, "reason": "Called customer"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Enquiry.Status.CONTACTED)
        event = AuditEvent.objects.get(entity_id=self.enquiry.pk)
        self.assertEqual(event.action, "status_changed")
        self.assertEqual(event.actor, self.staff)
        self.assertEqual(event.before_data, {"status": Enquiry.Status.NEW})
        self.assertEqual(event.after_data, {"status": Enquiry.Status.CONTACTED})
        self.assertEqual(event.reason, "Called customer")

    def test_transition_endpoint_rejects_invalid_transition(self):
        response = self.client.post(
            f"/api/enquiries/{self.enquiry.pk}/transition/",
            {"status": Enquiry.Status.CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.NEW)
        self.assertFalse(AuditEvent.objects.exists())

    def test_followup_complete_endpoint_updates_and_audits(self):
        response = self.client.post(
            f"/api/follow-ups/{self.follow_up.pk}/complete/",
            {"note": "Customer confirmed receipt of quotation"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], FollowUp.Status.COMPLETED)
        self.assertIsNotNone(response.data["completed_at"])
        self.follow_up.refresh_from_db()
        self.assertEqual(
            self.follow_up.note, "Customer confirmed receipt of quotation"
        )
        event = AuditEvent.objects.get(entity_id=self.follow_up.pk)
        self.assertEqual(event.action, "completed")
        self.assertEqual(event.actor, self.staff)

    def test_completed_followup_cannot_be_completed_again(self):
        first = self.client.post(
            f"/api/follow-ups/{self.follow_up.pk}/complete/",
            {"note": "First completion"},
            format="json",
        )
        second = self.client.post(
            f"/api/follow-ups/{self.follow_up.pk}/complete/",
            {"note": "Second completion"},
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(
            AuditEvent.objects.filter(entity_id=self.follow_up.pk).count(), 1
        )

    def test_staff_cannot_transition_enquiry_in_another_division(self):
        other_enquiry = Enquiry.objects.create(
            enquiry_number="CRM-ACTION-E2",
            customer=self.customer,
            division=self.other_division,
            source=Enquiry.Source.PHONE,
            requested_product_service="Restricted service",
            created_by=self.other_staff,
        )

        response = self.client.post(
            f"/api/enquiries/{other_enquiry.pk}/transition/",
            {"status": Enquiry.Status.CONTACTED},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(AuditEvent.objects.filter(entity_id=other_enquiry.pk).exists())

    def test_staff_cannot_complete_followup_in_another_division(self):
        other_enquiry = Enquiry.objects.create(
            enquiry_number="CRM-ACTION-E3",
            customer=self.customer,
            division=self.other_division,
            source=Enquiry.Source.PHONE,
            requested_product_service="Restricted service",
            created_by=self.other_staff,
        )
        other_follow_up = FollowUp.objects.create(
            enquiry=other_enquiry,
            due_at=timezone.now() + timezone.timedelta(days=1),
        )

        response = self.client.post(
            f"/api/follow-ups/{other_follow_up.pk}/complete/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            AuditEvent.objects.filter(entity_id=other_follow_up.pk).exists()
        )
    def test_enquiry_status_cannot_be_set_or_changed_directly(self):
        create_response = self.client.post(
            "/api/enquiries/",
            {
                "enquiry_number": "CRM-ACTION-E4",
                "customer": str(self.customer.pk),
                "division": str(self.division.pk),
                "source": "phone",
                "requested_product_service": "Direct status attempt",
                "status": "confirmed",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["status"], Enquiry.Status.NEW)

        update_response = self.client.patch(
            f"/api/enquiries/{self.enquiry.pk}/",
            {"status": "lost"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.NEW)
        self.assertFalse(AuditEvent.objects.filter(entity_id=self.enquiry.pk).exists())

    def test_followup_status_and_completion_time_are_read_only(self):
        create_response = self.client.post(
            "/api/follow-ups/",
            {
                "enquiry": str(self.enquiry.pk),
                "due_at": (timezone.now() + timezone.timedelta(days=2)).isoformat(),
                "status": "completed",
                "completed_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        created = FollowUp.objects.get(pk=create_response.data["id"])
        self.assertEqual(created.status, FollowUp.Status.OPEN)
        self.assertIsNone(created.completed_at)

        update_response = self.client.patch(
            f"/api/follow-ups/{self.follow_up.pk}/",
            {"status": "completed", "completed_at": timezone.now().isoformat()},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.follow_up.refresh_from_db()
        self.assertEqual(self.follow_up.status, FollowUp.Status.OPEN)
        self.assertIsNone(self.follow_up.completed_at)
        self.assertFalse(AuditEvent.objects.filter(entity_id=self.follow_up.pk).exists())

