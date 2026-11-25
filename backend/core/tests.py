from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Customer, DesignRecord, DesignRevision, Division, Enquiry, JobCard,
    SalesOrder, StaffDivision, StaffProfile, StoredFile, DesignRevisionFile, Role, StaffRole,
)


class DomainModelTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(code="creatives", name="SADACO Creatives")
        self.user = get_user_model().objects.create_user(username="designer", password="test-password-123")
        self.staff = StaffProfile.objects.create(user=self.user, display_name="Test Designer")
        StaffDivision.objects.create(staff=self.staff, division=self.division)

    def test_department_name_is_unique_within_division(self):
        from .models import Department
        Department.objects.create(division=self.division, name="Design")
        with self.assertRaises(Exception):
            Department.objects.create(division=self.division, name="Design")

    def test_active_staff_role_scope_is_unique_when_nullable_scope_fields_are_empty(self):
        role = Role.objects.create(code="manager-test", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=role)
        with self.assertRaises(Exception):
            StaffRole.objects.create(staff=self.staff, role=role)

    def test_active_staff_role_is_unique_per_division_scope(self):
        role = Role.objects.create(code="designer-test", name="Designer")
        StaffRole.objects.create(staff=self.staff, role=role, division=self.division)
        with self.assertRaises(Exception):
            StaffRole.objects.create(staff=self.staff, role=role, division=self.division)

    def test_job_card_requires_approved_locked_design_revision(self):
        customer = Customer.objects.create(customer_code="C-001", display_name="Test Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-2026-0001", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("1000"), grand_total=Decimal("1000"),
            balance_due=Decimal("1000"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Front sign")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="submitted", created_by=self.staff
        )
        job = JobCard(
            job_number="JOB-001", sales_order=order,
            approved_design_revision=revision, division=self.division,
        )
        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_locked_revision_file_attachments_cannot_be_added_or_removed(self):
        customer = Customer.objects.create(customer_code="C-003", display_name="Test Customer 3")
        order = SalesOrder.objects.create(
            order_number="SAD-2026-0003", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Approved artwork")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="approved",
            locked_at=timezone.now(), created_by=self.staff,
        )
        stored_file = StoredFile.objects.create(
            storage_key="designs/approved-artwork.pdf",
            original_name="approved-artwork.pdf",
            mime_type="application/pdf",
            byte_size=1024,
            uploaded_by=self.staff,
        )

        with self.assertRaises(ValidationError):
            with transaction.atomic():
                revision.files.add(stored_file)
        with self.assertRaises(ValidationError):
            DesignRevisionFile.objects.create(
                design_revision=revision, stored_file=stored_file
            )

        unlocked = DesignRevision.objects.create(
            design_record=design, revision_number=2, status="pending",
            created_by=self.staff,
        )
        unlocked.files.add(stored_file)
        unlocked.locked_at = timezone.now()
        unlocked.status = "approved"
        unlocked.save()

        with self.assertRaises(ValidationError):
            with transaction.atomic():
                unlocked.files.remove(stored_file)
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                unlocked.files.clear()
        with self.assertRaises(ValidationError):
            DesignRevisionFile.objects.filter(
                design_revision=unlocked
            ).delete()

    def test_approved_revision_is_immutable(self):
        customer = Customer.objects.create(customer_code="C-002", display_name="Test Customer 2")
        order = SalesOrder.objects.create(
            order_number="SAD-2026-0002", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("500"), grand_total=Decimal("500"),
            balance_due=Decimal("500"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Logo")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="approved",
            locked_at=timezone.now(), created_by=self.staff,
        )
        revision.change_summary = "Edited after approval"
        with self.assertRaises(ValidationError):
            revision.save()


class EnquiryAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.division_a = Division.objects.create(code="creatives", name="SADACO Creatives")
        self.division_b = Division.objects.create(code="cnc", name="SADACO CNC")
        User = get_user_model()
        self.user_a = User.objects.create_user(username="staff-a", password="password123")
        self.user_b = User.objects.create_user(username="staff-b", password="password123")
        self.staff_a = StaffProfile.objects.create(user=self.user_a, display_name="Staff A")
        self.staff_b = StaffProfile.objects.create(user=self.user_b, display_name="Staff B")
        StaffDivision.objects.create(staff=self.staff_a, division=self.division_a)
        StaffDivision.objects.create(staff=self.staff_b, division=self.division_b)
        self.customer = Customer.objects.create(customer_code="C-100", display_name="Customer")

    def test_staff_only_sees_enquiries_in_assigned_division(self):
        Enquiry.objects.create(
            enquiry_number="ENQ-A", customer=self.customer, division=self.division_a,
            source=Enquiry.Source.PHONE, requested_product_service="A", created_by=self.staff_a,
        )
        Enquiry.objects.create(
            enquiry_number="ENQ-B", customer=self.customer, division=self.division_b,
            source=Enquiry.Source.PHONE, requested_product_service="B", created_by=self.staff_b,
        )
        self.client.force_authenticate(self.user_a)
        response = self.client.get("/api/enquiries/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["enquiry_number"], "ENQ-A")

    def test_staff_cannot_create_enquiry_in_unassigned_division(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post("/api/enquiries/", {
            "enquiry_number": "ENQ-X", "customer": str(self.customer.id),
            "division": str(self.division_b.id), "source": "phone",
            "requested_product_service": "Restricted enquiry",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_api_request_is_denied(self):
        response = self.client.get("/api/enquiries/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_without_staff_profile_is_denied(self):
        user = get_user_model().objects.create_user(username="no-staff", password="password123")
        self.client.force_authenticate(user)
        response = self.client.get("/api/enquiries/")
        self.assertEqual(response.status_code, 403)

    def test_inactive_staff_is_denied(self):
        self.staff_a.employment_status = "inactive"
        self.staff_a.save()
        self.client.force_authenticate(self.user_a)
        response = self.client.get("/api/enquiries/")
        self.assertEqual(response.status_code, 403)

    def test_enquiry_cannot_assign_staff_from_other_division(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.post("/api/enquiries/", {
            "enquiry_number": "ENQ-CROSS", "customer": str(self.customer.id),
            "division": str(self.division_a.id), "source": "phone",
            "requested_product_service": "Design",
            "assigned_to": str(self.staff_b.id),
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_to", response.data)

    def test_followup_cannot_assign_staff_from_other_division(self):
        enquiry = Enquiry.objects.create(
            enquiry_number="ENQ-FOLLOW", customer=self.customer,
            division=self.division_a, source=Enquiry.Source.PHONE,
            requested_product_service="Design", created_by=self.staff_a,
        )
        self.client.force_authenticate(self.user_a)
        response = self.client.post("/api/follow-ups/", {
            "enquiry": str(enquiry.id),
            "assigned_to": str(self.staff_b.id),
            "due_at": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("assigned_to", response.data)


class CRMServiceTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(code="service-test", name="Service Test Division")
        user = get_user_model().objects.create_user(username="crm-actor", password="password123")
        self.actor = StaffProfile.objects.create(user=user, display_name="CRM Actor")
        self.customer = Customer.objects.create(customer_code="CRM-001", display_name="CRM Customer")
        self.enquiry = Enquiry.objects.create(
            enquiry_number="CRM-ENQ-001", customer=self.customer,
            division=self.division, source=Enquiry.Source.PHONE,
            requested_product_service="Test work", created_by=self.actor,
        )

    def test_valid_enquiry_transition_creates_audit_event(self):
        from .models import AuditEvent
        from .services import transition_enquiry
        updated = transition_enquiry(
            enquiry_id=self.enquiry.id,
            target_status=Enquiry.Status.CONTACTED,
            actor=self.actor,
            reason="Initial customer contact",
        )
        self.assertEqual(updated.status, Enquiry.Status.CONTACTED)
        event = AuditEvent.objects.get(entity_id=self.enquiry.id)
        self.assertEqual(event.action, "status_changed")
        self.assertEqual(event.before_data["status"], Enquiry.Status.NEW)
        self.assertEqual(event.after_data["status"], Enquiry.Status.CONTACTED)

    def test_invalid_enquiry_transition_is_rejected_without_audit(self):
        from django.core.exceptions import ValidationError
        from .models import AuditEvent
        from .services import transition_enquiry
        with self.assertRaises(ValidationError):
            transition_enquiry(
                enquiry_id=self.enquiry.id,
                target_status=Enquiry.Status.CONFIRMED,
                actor=self.actor,
            )
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, Enquiry.Status.NEW)
        self.assertFalse(AuditEvent.objects.exists())

    def test_followup_can_only_be_completed_once(self):
        from django.core.exceptions import ValidationError
        from .models import AuditEvent, FollowUp
        from .services import complete_follow_up
        follow_up = FollowUp.objects.create(
            enquiry=self.enquiry, due_at=timezone.now() + timezone.timedelta(days=1),
        )
        completed = complete_follow_up(follow_up_id=follow_up.id, actor=self.actor, note="Called customer")
        self.assertEqual(completed.status, FollowUp.Status.COMPLETED)
        self.assertIsNotNone(completed.completed_at)
        self.assertEqual(AuditEvent.objects.filter(entity_id=follow_up.id).count(), 1)
        with self.assertRaises(ValidationError):
            complete_follow_up(follow_up_id=follow_up.id, actor=self.actor)
        self.assertEqual(AuditEvent.objects.filter(entity_id=follow_up.id).count(), 1)
