from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
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
        with self.assertRaises(ValidationError):
            job.save()

    def test_job_card_bulk_create_rejects_unapproved_design_revision(self):
        customer = Customer.objects.create(customer_code="C-BULK-001", display_name="Bulk Test Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-BULK-0001", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Unapproved artwork")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="submitted", created_by=self.staff,
        )
        job = JobCard(
            job_number="JOB-BULK-001", sales_order=order,
            approved_design_revision=revision, division=self.division,
        )
        with self.assertRaises(ValidationError):
            JobCard.objects.bulk_create([job])
        self.assertFalse(JobCard.objects.filter(job_number="JOB-BULK-001").exists())

    def test_job_card_queryset_bulk_mutations_are_disabled(self):
        job = JobCard(job_number="JOB-BULK-UPDATE", division=self.division)
        with self.assertRaises(ValidationError):
            JobCard.objects.filter(job_number="missing").update(status="released")
        with self.assertRaises(ValidationError):
            JobCard.objects.bulk_update([job], ["status"])

    def test_locked_revision_file_attachments_cannot_be_added_or_removed(self):
        customer = Customer.objects.create(customer_code="C-003", display_name="Test Customer 3")
        order = SalesOrder.objects.create(
            order_number="SAD-2026-0003", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Approved artwork")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="pending",
            created_by=self.staff,
        )
        revision.status = "approved"
        revision.locked_at = timezone.now()
        revision.save()
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
            with transaction.atomic():
                stored_file.design_revisions.add(revision)
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
                stored_file.design_revisions.remove(unlocked)
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                stored_file.design_revisions.clear()
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
        with self.assertRaises(ValidationError):
            DesignRevision.objects.create(
                design_record=design, revision_number=99, status="approved",
                locked_at=timezone.now(), created_by=self.staff,
            )
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="draft",
            created_by=self.staff,
        )
        revision.status = "approved"
        revision.locked_at = timezone.now()
        revision.save()
        revision.change_summary = "Edited after approval"
        with self.assertRaises(ValidationError):
            revision.save()
        with self.assertRaises(ValidationError):
            DesignRevision.objects.filter(pk=revision.pk).update(
                change_summary="Queryset bypass attempt"
            )
        revision.change_summary = "Bulk update bypass attempt"
        with self.assertRaises(ValidationError):
            DesignRevision.objects.bulk_update([revision], ["change_summary"])
        with self.assertRaises(ValidationError):
            DesignRevision.objects.filter(pk=revision.pk).delete()
        with self.assertRaises(ValidationError):
            revision.delete()
        with self.assertRaises(ValidationError):
            DesignRevision.objects.bulk_create([DesignRevision(
                design_record=design,
                revision_number=2,
                status="approved",
                locked_at=timezone.now(),
                created_by=self.staff,
            )])


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


class DesignApprovalServiceTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(code="approval", name="Approval Division")
        User = get_user_model()
        self.manager_user = User.objects.create_user(username="approval-manager", password="test-password-123")
        self.manager = StaffProfile.objects.create(user=self.manager_user, display_name="Approval Manager")
        self.designer_user = User.objects.create_user(username="approval-designer", password="test-password-123")
        self.designer = StaffProfile.objects.create(user=self.designer_user, display_name="Approval Designer")
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.manager, role=manager_role, division=self.division)
        customer = Customer.objects.create(customer_code="APR-001", display_name="Approval Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-APPROVAL-001", customer=customer, division=self.division,
            created_by=self.manager, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Approval Artwork")
        self.revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="submitted", created_by=self.designer,
        )

    def test_manager_confirmation_requires_customer_approval_first(self):
        from .services import record_design_approval
        with self.assertRaises(ValidationError):
            record_design_approval(
                revision_id=self.revision.pk, reviewer_type="manager",
                decision="approved", actor=self.manager,
            )
        self.assertFalse(self.revision.approvals.exists())
        self.revision.refresh_from_db()
        self.assertIsNone(self.revision.locked_at)

    def test_customer_approval_then_manager_confirmation_locks_revision_and_audits(self):
        from .models import AuditEvent
        from .services import record_design_approval
        customer_decision = record_design_approval(
            revision_id=self.revision.pk, reviewer_type="customer",
            decision="approved", actor=self.manager, comments="Customer confirmed final artwork",
        )
        self.assertEqual(customer_decision.decision, "approved")
        self.revision.refresh_from_db()
        self.assertIsNone(self.revision.locked_at)
        manager_decision = record_design_approval(
            revision_id=self.revision.pk, reviewer_type="manager",
            decision="approved", actor=self.manager, comments="Manager confirmed for production",
        )
        self.assertEqual(manager_decision.reviewer_type, "manager")
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, "approved")
        self.assertIsNotNone(self.revision.locked_at)
        self.assertEqual(self.revision.approvals.count(), 2)
        self.assertEqual(AuditEvent.objects.filter(entity_id=self.revision.pk).count(), 2)
        self.assertEqual(AuditEvent.objects.filter(entity_id=customer_decision.pk).count(), 1)
        self.assertEqual(AuditEvent.objects.filter(entity_id=manager_decision.pk).count(), 1)

    def test_revision_required_decision_does_not_lock_revision(self):
        from .services import record_design_approval
        record_design_approval(
            revision_id=self.revision.pk, reviewer_type="customer",
            decision="revision_required", actor=self.manager, comments="Change requested",
        )
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, "revision_required")
        self.assertIsNone(self.revision.locked_at)

    def test_non_manager_cannot_record_design_approval(self):
        from .services import record_design_approval
        with self.assertRaises(ValidationError):
            record_design_approval(
                revision_id=self.revision.pk, reviewer_type="customer",
                decision="approved", actor=self.designer,
            )
        self.assertFalse(self.revision.approvals.exists())

    def test_design_approval_history_cannot_be_edited_or_deleted(self):
        from .models import DesignApproval
        from .services import record_design_approval
        approval = record_design_approval(
            revision_id=self.revision.pk, reviewer_type="customer",
            decision="approved", actor=self.manager, comments="Recorded decision",
        )
        approval.comments = "Tampered history"
        with self.assertRaises(ValidationError):
            approval.save()
        with self.assertRaises(ValidationError):
            DesignApproval.objects.filter(pk=approval.pk).update(comments="Queryset tamper")
        with self.assertRaises(ValidationError):
            DesignApproval.objects.filter(pk=approval.pk).delete()
        with self.assertRaises(ValidationError):
            DesignApproval.objects.bulk_update([approval], ["comments"])
        with self.assertRaises(ValidationError):
            approval.delete()
        self.assertEqual(DesignApproval.objects.get(pk=approval.pk).comments, "Recorded decision")

        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_designapproval SET comments = %s WHERE id = %s",
                        ["Raw SQL tamper", str(approval.pk)],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM core_designapproval WHERE id = %s",
                        [str(approval.pk)],
                    )
        self.assertEqual(DesignApproval.objects.get(pk=approval.pk).comments, "Recorded decision")


class DesignApprovalAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.division = Division.objects.create(code="approval-api", name="Approval API Division")
        User = get_user_model()
        self.manager_user = User.objects.create_user(username="approval-api-manager", password="password123")
        self.manager = StaffProfile.objects.create(user=self.manager_user, display_name="API Manager")
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.manager, role=manager_role, division=self.division)
        self.designer_user = User.objects.create_user(username="approval-api-designer", password="password123")
        self.designer = StaffProfile.objects.create(user=self.designer_user, display_name="API Designer")
        StaffDivision.objects.create(staff=self.designer, division=self.division)
        customer = Customer.objects.create(customer_code="APR-API-001", display_name="API Approval Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-APPROVAL-API-001", customer=customer, division=self.division,
            created_by=self.manager, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="API Approval Artwork")
        self.revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="submitted", created_by=self.designer,
        )
        self.approval_url = f"/api/design-revisions/{self.revision.pk}/approval/"

    def test_customer_and_manager_approval_api_flow_locks_revision(self):
        from .models import AuditEvent
        self.client.force_authenticate(self.manager_user)
        customer_response = self.client.post(self.approval_url, {
            "reviewer_type": "customer",
            "decision": "approved",
            "comments": "Customer approved the final artwork",
        }, format="json")
        self.assertEqual(customer_response.status_code, 201)
        manager_response = self.client.post(self.approval_url, {
            "reviewer_type": "manager",
            "decision": "approved",
            "comments": "Confirmed for production",
        }, format="json")
        self.assertEqual(manager_response.status_code, 201)
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, "approved")
        self.assertIsNotNone(self.revision.locked_at)
        detail = self.client.get(f"/api/design-revisions/{self.revision.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["approvals"]), 2)
        self.assertEqual(AuditEvent.objects.filter(entity_id=self.revision.pk).count(), 2)

    def test_design_revision_api_is_read_only(self):
        self.client.force_authenticate(self.manager_user)
        response = self.client.patch(
            f"/api/design-revisions/{self.revision.pk}/",
            {"change_summary": "Attempted edit"},
            format="json",
        )
        self.assertEqual(response.status_code, 405)

    def test_staff_outside_division_cannot_read_or_approve_revision(self):
        other_division = Division.objects.create(code="approval-api-other", name="Other API Division")
        other_user = get_user_model().objects.create_user(username="approval-api-outsider", password="password123")
        other_staff = StaffProfile.objects.create(user=other_user, display_name="Outside Staff")
        StaffDivision.objects.create(staff=other_staff, division=other_division)
        self.client.force_authenticate(other_user)
        response = self.client.post(self.approval_url, {
            "reviewer_type": "customer", "decision": "approved",
        }, format="json")
        self.assertEqual(response.status_code, 404)

    def test_designer_cannot_record_customer_or_manager_approval(self):
        self.client.force_authenticate(self.designer_user)
        response = self.client.post(self.approval_url, {
            "reviewer_type": "customer", "decision": "approved",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.revision.approvals.count(), 0)
