from decimal import Decimal
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    ApprovalRequest, Customer, CustomerCommunication, DesignRecord, DesignRevision, Division, Enquiry, FollowUp, JobCard, Quotation,
    OrderAssignment, ProductionStage, ProductionUpdate, SalesOrder, StaffDivision,
    StaffProfile, StaffTask, StoredFile, DesignRevisionFile, Role, StaffRole,
)


class DomainModelTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(code="creatives", name="SADACO Creatives")
        self.user = get_user_model().objects.create_user(username="designer", password="test-password-123")
        self.staff = StaffProfile.objects.create(user=self.user, display_name="Test Designer")
        StaffDivision.objects.create(staff=self.staff, division=self.division)

    def test_enquiry_and_followup_model_division_scope_is_enforced(self):
        other_division = Division.objects.create(code="enquiry-other", name="Enquiry Other Division")
        other_user = get_user_model().objects.create_user(
            username="enquiry-other-staff", password="test-password-123"
        )
        other_staff = StaffProfile.objects.create(
            user=other_user, display_name="Enquiry Other Staff"
        )
        StaffDivision.objects.create(staff=other_staff, division=other_division)
        customer = Customer.objects.create(
            customer_code="C-ENQUIRY-SCOPE", display_name="Enquiry Scope Customer"
        )
        with self.assertRaises(ValidationError):
            Enquiry.objects.create(
                enquiry_number="ENQ-BAD-ASSIGNEE", customer=customer,
                division=self.division, source=Enquiry.Source.DIRECT,
                requested_product_service="Signage", assigned_to=other_staff,
                created_by=self.staff,
            )
        with self.assertRaises(ValidationError):
            Enquiry.objects.create(
                enquiry_number="ENQ-BAD-CREATOR", customer=customer,
                division=self.division, source=Enquiry.Source.DIRECT,
                requested_product_service="Signage", created_by=other_staff,
            )
        enquiry = Enquiry.objects.create(
            enquiry_number="ENQ-VALID-SCOPE", customer=customer,
            division=self.division, source=Enquiry.Source.DIRECT,
            requested_product_service="Signage", assigned_to=self.staff,
            created_by=self.staff,
        )
        with self.assertRaises(ValidationError):
            FollowUp.objects.create(
                enquiry=enquiry, assigned_to=other_staff,
                due_at=timezone.now(),
            )

    def test_enquiry_and_followup_database_guards_reject_raw_cross_division_assignments(self):
        other_division = Division.objects.create(code="enquiry-raw-other", name="Enquiry Raw Other")
        other_user = get_user_model().objects.create_user(
            username="enquiry-raw-other-staff", password="test-password-123"
        )
        other_staff = StaffProfile.objects.create(
            user=other_user, display_name="Enquiry Raw Other Staff"
        )
        StaffDivision.objects.create(staff=other_staff, division=other_division)
        customer = Customer.objects.create(
            customer_code="C-ENQUIRY-RAW", display_name="Enquiry Raw Customer"
        )
        enquiry = Enquiry.objects.create(
            enquiry_number="ENQ-RAW-SCOPE", customer=customer,
            division=self.division, source=Enquiry.Source.DIRECT,
            requested_product_service="Signage", assigned_to=self.staff,
            created_by=self.staff,
        )
        followup = FollowUp.objects.create(
            enquiry=enquiry, assigned_to=self.staff, due_at=timezone.now(),
        )
        cases = [
            ("core_enquiry", "assigned_to_id", other_staff.pk, enquiry.pk),
            ("core_enquiry", "created_by_id", other_staff.pk, enquiry.pk),
            ("core_followup", "assigned_to_id", other_staff.pk, followup.pk),
        ]
        for table, column, value, row_id in cases:
            with self.subTest(table=table, column=column):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f'UPDATE "{table}" SET "{column}" = %s WHERE "id" = %s',
                                [value, row_id],
                            )

    def test_global_founder_can_create_enquiry_without_staff_division_membership(self):
        founder_user = get_user_model().objects.create_user(
            username="enquiry-global-founder", password="test-password-123"
        )
        founder = StaffProfile.objects.create(user=founder_user, display_name="Enquiry Global Founder")
        founder_role = Role.objects.create(code="founder", name="Founder")
        StaffRole.objects.create(staff=founder, role=founder_role)
        customer = Customer.objects.create(
            customer_code="C-ENQUIRY-FOUNDER", display_name="Enquiry Founder Customer"
        )
        enquiry = Enquiry.objects.create(
            enquiry_number="ENQ-GLOBAL-FOUNDER", customer=customer,
            division=self.division, source=Enquiry.Source.DIRECT,
            requested_product_service="Signage", created_by=founder,
        )
        self.assertEqual(enquiry.created_by_id, founder.pk)

    def test_global_founder_can_create_sales_order_without_staff_division_membership(self):
        founder_user = get_user_model().objects.create_user(username="global-founder", password="test-password-123")
        founder = StaffProfile.objects.create(user=founder_user, display_name="Global Founder")
        founder_role = Role.objects.create(code="founder", name="Founder")
        StaffRole.objects.create(staff=founder, role=founder_role)
        customer = Customer.objects.create(customer_code="GLOBAL-FOUNDER-C", display_name="Founder Customer")

        order = SalesOrder.objects.create(
            order_number="SAD-GLOBAL-FOUNDER", customer=customer, division=self.division,
            created_by=founder, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        self.assertEqual(order.created_by_id, founder.pk)

    def test_division_scoped_founder_is_not_global(self):
        founder_user = get_user_model().objects.create_user(username="scoped-founder", password="test-password-123")
        founder = StaffProfile.objects.create(user=founder_user, display_name="Scoped Founder")
        founder_role = Role.objects.create(code="founder", name="Founder")
        StaffRole.objects.create(staff=founder, role=founder_role, division=self.division)

        from .permissions import is_founder
        self.assertFalse(is_founder(founder))
        customer = Customer.objects.create(customer_code="SCOPED-FOUNDER-C", display_name="Scoped Founder Customer")
        with self.assertRaises(ValidationError):
            SalesOrder.objects.create(
                order_number="SAD-SCOPED-FOUNDER", customer=customer, division=self.division,
                created_by=founder, subtotal=Decimal("100"), grand_total=Decimal("100"),
                balance_due=Decimal("100"),
            )

    def test_global_founder_database_guard_allows_sales_order_creator(self):
        founder_user = get_user_model().objects.create_user(username="global-founder-db", password="test-password-123")
        founder = StaffProfile.objects.create(user=founder_user, display_name="Global Founder DB")
        founder_role = Role.objects.create(code="super_admin", name="Super Admin")
        StaffRole.objects.create(staff=founder, role=founder_role)
        customer = Customer.objects.create(customer_code="GLOBAL-DB-C", display_name="Global DB Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-GLOBAL-DB", customer=customer, division=self.division,
            created_by=founder, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        self.assertTrue(SalesOrder.objects.filter(pk=order.pk).exists())

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

    def test_job_card_database_guard_blocks_invalid_raw_insert_and_update(self):
        customer = Customer.objects.create(customer_code="C-DB-GUARD", display_name="DB Guard Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-DB-GUARD", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="DB guard artwork")
        approved_revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="pending", created_by=self.staff,
        )
        unapproved_revision = DesignRevision.objects.create(
            design_record=design, revision_number=2, status="submitted", created_by=self.staff,
        )

        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=manager_role, division=self.division)
        from .services import record_design_approval
        record_design_approval(
            revision_id=approved_revision.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=approved_revision.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        approved_revision.refresh_from_db()
        self.assertEqual(approved_revision.status, "approved")
        self.assertIsNotNone(approved_revision.locked_at)

        invalid_job_id = uuid.uuid4()
        now = timezone.now()
        insert_sql = (
            'INSERT INTO "core_jobcard" '
            '("id", "created_at", "updated_at", "job_number", "sales_order_id", '
            '"approved_design_revision_id", "division_id", "status", "planned_start", '
            '"planned_completion", "actual_start", "actual_completion", "requirements", "notes") '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
        )
        insert_values = (
            invalid_job_id, now, now, "JOB-RAW-INVALID", order.pk,
            unapproved_revision.pk, self.division.pk, "pending",
            None, None, None, None, "", "",
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(insert_sql, insert_values)

        valid_job = JobCard.objects.create(
            job_number="JOB-DB-GUARD-VALID", sales_order=order,
            approved_design_revision=approved_revision, division=self.division,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        'UPDATE "core_jobcard" SET "approved_design_revision_id" = %s WHERE "id" = %s',
                        [unapproved_revision.pk, valid_job.pk],
                    )

    def test_production_and_task_assignments_must_match_division(self):
        other_division = Division.objects.create(code="cnc", name="SADACO CNC")
        other_user = get_user_model().objects.create_user(
            username="other-division-staff", password="test-password-123"
        )
        other_staff = StaffProfile.objects.create(
            user=other_user, display_name="Other Division Staff"
        )
        StaffDivision.objects.create(staff=other_staff, division=other_division)

        customer = Customer.objects.create(
            customer_code="C-DIV-GUARD", display_name="Division Guard Customer"
        )
        order = SalesOrder.objects.create(
            order_number="SAD-DIV-GUARD", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="Division guard design")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="pending", created_by=self.staff,
        )
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=manager_role, division=self.division)
        from .services import record_design_approval
        record_design_approval(
            revision_id=revision.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=revision.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        revision.refresh_from_db()
        job = JobCard.objects.create(
            job_number="JOB-DIV-GUARD", sales_order=order,
            approved_design_revision=revision, division=self.division,
        )

        with self.assertRaises(ValidationError):
            DesignRecord(
                sales_order=order, title="Wrong division assignee", assigned_to=other_staff
            ).save()
        with self.assertRaises(ValidationError):
            OrderAssignment(
                sales_order=order, staff=other_staff, assigned_by=self.staff,
                assignment_type="production",
            ).save()
        with self.assertRaises(ValidationError):
            ProductionStage(
                job_card=job, stage_code="cutting", stage_name="Cutting",
                sequence_number=1, assigned_to=other_staff,
            ).save()

        stage = ProductionStage.objects.create(
            job_card=job, stage_code="polishing", stage_name="Polishing",
            sequence_number=1,
        )
        with self.assertRaises(ValidationError):
            ProductionUpdate(
                production_stage=stage, staff=other_staff, status="in_progress"
            ).save()
        with self.assertRaises(ValidationError):
            StaffTask(
                task_number="TASK-DIV-GUARD", division=self.division,
                sales_order=order, job_card=job, production_stage=stage,
                assigned_to=other_staff, assigned_by=self.staff,
                title="Cross-division task", priority="normal",
            ).save()

    def test_quotation_and_sales_order_division_relationships_are_enforced(self):
        other_division = Division.objects.create(code="quote-other", name="Quotation Other Division")
        other_user = get_user_model().objects.create_user(
            username="quotation-other-staff", password="test-password-123"
        )
        other_staff = StaffProfile.objects.create(
            user=other_user, display_name="Quotation Other Staff"
        )
        StaffDivision.objects.create(staff=other_staff, division=other_division)
        customer = Customer.objects.create(
            customer_code="C-QUOTE-SCOPE", display_name="Quotation Scope Customer"
        )
        enquiry = Enquiry.objects.create(
            enquiry_number="ENQ-QUOTE-SCOPE", customer=customer,
            division=self.division, source=Enquiry.Source.DIRECT,
            requested_product_service="CNC signage", created_by=self.staff,
        )
        quotation = Quotation.objects.create(
            quotation_number="QUO-SCOPE-001", customer=customer,
            enquiry=enquiry, division=self.division, prepared_by=self.staff,
            subtotal=Decimal("100"), total_amount=Decimal("100"),
        )
        order = SalesOrder.objects.create(
            order_number="SAD-QUOTE-SCOPE", customer=customer,
            division=self.division, quotation=quotation, created_by=self.staff,
            subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )

        with self.assertRaises(ValidationError):
            Quotation(
                quotation_number="QUO-SCOPE-BAD-STAFF", customer=customer,
                division=self.division, prepared_by=other_staff,
            ).save()
        with self.assertRaises(ValidationError):
            SalesOrder(
                order_number="SAD-QUOTE-SCOPE-BAD", customer=customer,
                division=other_division, quotation=quotation, created_by=other_staff,
            ).save()

        for table, column, value, row_id in [
            ("core_quotation", "division_id", other_division.pk, quotation.pk),
            ("core_salesorder", "division_id", other_division.pk, order.pk),
        ]:
            with self.subTest(table=table):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f'UPDATE "{table}" SET "{column}" = %s WHERE "id" = %s',
                                [value, row_id],
                            )

    def test_database_guards_reject_raw_cross_division_staff_assignments(self):
        other_division = Division.objects.create(code="decor", name="SADACO Decor Co")
        other_user = get_user_model().objects.create_user(
            username="raw-other-division-staff", password="test-password-123"
        )
        other_staff = StaffProfile.objects.create(
            user=other_user, display_name="Other Division Staff"
        )
        StaffDivision.objects.create(staff=other_staff, division=other_division)

        customer = Customer.objects.create(
            customer_code="C-RAW-DIV-GUARD", display_name="Raw Division Guard Customer"
        )
        order = SalesOrder.objects.create(
            order_number="SAD-RAW-DIV-GUARD", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(
            sales_order=order, title="Raw guard design", assigned_to=self.staff
        )
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="pending", created_by=self.staff,
        )
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=manager_role, division=self.division)
        from .services import record_design_approval
        record_design_approval(
            revision_id=revision.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=revision.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        revision.refresh_from_db()
        job = JobCard.objects.create(
            job_number="JOB-RAW-DIV-GUARD", sales_order=order,
            approved_design_revision=revision, division=self.division,
        )
        stage = ProductionStage.objects.create(
            job_card=job, stage_code="assembly", stage_name="Assembly",
            sequence_number=1, assigned_to=self.staff,
        )
        update = ProductionUpdate.objects.create(
            production_stage=stage, staff=self.staff, status="in_progress"
        )
        assignment = OrderAssignment.objects.create(
            sales_order=order, staff=self.staff, assigned_by=self.staff,
            assignment_type="production",
        )
        task = StaffTask.objects.create(
            task_number="TASK-RAW-DIV-GUARD", division=self.division,
            sales_order=order, assigned_to=self.staff, assigned_by=self.staff,
            title="Valid division task", priority="normal",
        )

        invalid_updates = [
            ("core_designrecord", "assigned_to_id", other_staff.pk, design.pk),
            ("core_orderassignment", "staff_id", other_staff.pk, assignment.pk),
            ("core_productionstage", "assigned_to_id", other_staff.pk, stage.pk),
            ("core_productionupdate", "staff_id", other_staff.pk, update.pk),
            ("core_stafftask", "assigned_to_id", other_staff.pk, task.pk),
        ]
        for table, column, value, row_id in invalid_updates:
            with self.subTest(table=table):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f'UPDATE "{table}" SET "{column}" = %s WHERE "id" = %s',
                                [value, row_id],
                            )

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
        from .services import record_design_approval
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=manager_role, division=self.division)
        record_design_approval(
            revision_id=revision.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=revision.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        revision.refresh_from_db()
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
        record_design_approval(
            revision_id=unlocked.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=unlocked.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        unlocked.refresh_from_db()

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

        replacement_file = StoredFile.objects.create(
            storage_key="designs/replacement.pdf",
            original_name="replacement.pdf",
            mime_type="application/pdf",
            byte_size=2048,
            uploaded_by=self.staff,
        )
        locked_attachment = DesignRevisionFile.objects.get(
            design_revision=unlocked, stored_file=stored_file
        )
        locked_attachment.stored_file = replacement_file
        with self.assertRaises(ValidationError):
            DesignRevisionFile.objects.bulk_update(
                [locked_attachment], ["stored_file"]
            )

        movable_revision = DesignRevision.objects.create(
            design_record=design, revision_number=3, status="pending",
            created_by=self.staff,
        )
        movable_revision.files.add(replacement_file)
        movable_attachment = DesignRevisionFile.objects.get(
            design_revision=movable_revision, stored_file=replacement_file
        )
        movable_attachment.design_revision = revision
        with self.assertRaises(ValidationError):
            DesignRevisionFile.objects.bulk_update(
                [movable_attachment], ["design_revision"]
            )

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
        with self.assertRaises(ValidationError):
            revision.save()
        with self.assertRaises(ValidationError):
            DesignRevision.objects.filter(pk=revision.pk).update(
                status="approved", locked_at=timezone.now()
            )
        revision.refresh_from_db()
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=manager_role, division=self.division)
        from .services import record_design_approval
        record_design_approval(
            revision_id=revision.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=revision.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        revision.refresh_from_db()
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
            DesignRevision.objects.bulk_update([revision], ["status", "locked_at"])
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


        self.assertEqual(DesignRevision.objects.get(pk=revision.pk).change_summary, "")

    def test_database_rejects_raw_sql_lock_without_approval_and_mutation_after_lock(self):
        customer = Customer.objects.create(customer_code="C-DB-GUARD", display_name="DB Guard Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-DB-GUARD", customer=customer, division=self.division,
            created_by=self.staff, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(sales_order=order, title="DB Guard Design")
        revision = DesignRevision.objects.create(
            design_record=design, revision_number=1, status="submitted", created_by=self.staff,
        )
        stored_file = StoredFile.objects.create(
            storage_key="designs/db-guard-original.pdf",
            original_name="db-guard-original.pdf",
            mime_type="application/pdf",
            byte_size=1024,
            uploaded_by=self.staff,
        )
        replacement_file = StoredFile.objects.create(
            storage_key="designs/db-guard-replacement.pdf",
            original_name="db-guard-replacement.pdf",
            mime_type="application/pdf",
            byte_size=1024,
            uploaded_by=self.staff,
        )
        revision.files.add(stored_file)
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_designrevision SET status = %s, locked_at = %s WHERE id = %s",
                        ["approved", timezone.now(), revision.pk.hex],
                    )

        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(staff=self.staff, role=manager_role, division=self.division)
        from .services import record_design_approval
        record_design_approval(
            revision_id=revision.pk, reviewer_type="customer",
            decision="approved", actor=self.staff,
        )
        record_design_approval(
            revision_id=revision.pk, reviewer_type="manager",
            decision="approved", actor=self.staff,
        )
        attachment = DesignRevisionFile.objects.get(
            design_revision=revision, stored_file=stored_file
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_designrevisionfile (id, design_revision_id, stored_file_id) VALUES (%s, %s, %s)",
                        [uuid.uuid4().hex, revision.pk.hex, replacement_file.pk.hex],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_designrevisionfile SET stored_file_id = %s WHERE id = %s",
                        [replacement_file.pk.hex, attachment.pk.hex],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM core_designrevisionfile WHERE id = %s",
                        [attachment.pk.hex],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_designrevision SET change_summary = %s WHERE id = %s",
                        ["Raw SQL mutation", revision.pk.hex],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM core_designrevision WHERE id = %s",
                        [revision.pk.hex],
                    )


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
        StaffDivision.objects.create(staff=self.actor, division=self.division)
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
        StaffDivision.objects.create(staff=self.manager, division=self.division)
        StaffDivision.objects.create(staff=self.designer, division=self.division)
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
                        ["Raw SQL tamper", approval.pk.hex],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM core_designapproval WHERE id = %s",
                        [approval.pk.hex],
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
        StaffDivision.objects.create(staff=self.manager, division=self.division)
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



class CRMRelationshipScopeTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(code="crm-scope", name="CRM Scope Division")
        self.other_division = Division.objects.create(code="crm-other", name="CRM Other Division")
        User = get_user_model()
        self.user = User.objects.create_user(username="crm-scope-staff", password="test-password-123")
        self.staff = StaffProfile.objects.create(user=self.user, display_name="CRM Scope Staff")
        StaffDivision.objects.create(staff=self.staff, division=self.division)
        self.other_user = User.objects.create_user(username="crm-outsider", password="test-password-123")
        self.outsider = StaffProfile.objects.create(user=self.other_user, display_name="CRM Outsider")
        StaffDivision.objects.create(staff=self.outsider, division=self.other_division)
        self.customer = Customer.objects.create(
            customer_code="CRM-SCOPE-CUSTOMER", display_name="CRM Scope Customer"
        )
        self.other_customer = Customer.objects.create(
            customer_code="CRM-OTHER-CUSTOMER", display_name="CRM Other Customer"
        )
        self.enquiry = Enquiry.objects.create(
            enquiry_number="CRM-SCOPE-ENQUIRY", customer=self.customer,
            division=self.division, source=Enquiry.Source.DIRECT,
            requested_product_service="CNC signage", created_by=self.staff,
        )
        self.other_enquiry = Enquiry.objects.create(
            enquiry_number="CRM-OTHER-ENQUIRY", customer=self.other_customer,
            division=self.other_division, source=Enquiry.Source.DIRECT,
            requested_product_service="Decor panel", created_by=self.outsider,
        )

    def test_customer_communication_model_scope_is_enforced(self):
        with self.assertRaises(ValidationError):
            CustomerCommunication.objects.create(
                customer=self.customer, enquiry=self.other_enquiry,
                division=self.division, channel=CustomerCommunication.Channel.PHONE,
                summary="Wrong enquiry division", recorded_by=self.staff,
            )
        with self.assertRaises(ValidationError):
            CustomerCommunication.objects.create(
                customer=self.other_customer, enquiry=self.enquiry,
                division=self.division, channel=CustomerCommunication.Channel.PHONE,
                summary="Wrong enquiry customer", recorded_by=self.staff,
            )
        with self.assertRaises(ValidationError):
            CustomerCommunication.objects.create(
                customer=self.customer, enquiry=self.enquiry,
                division=self.division, channel=CustomerCommunication.Channel.PHONE,
                summary="Wrong recorder", recorded_by=self.outsider,
            )
        communication = CustomerCommunication.objects.create(
            customer=self.customer, enquiry=self.enquiry, division=self.division,
            channel=CustomerCommunication.Channel.PHONE,
            summary="Valid customer call", recorded_by=self.staff,
        )
        self.assertEqual(communication.pk, CustomerCommunication.objects.get(pk=communication.pk).pk)

    def test_approval_request_model_scope_is_enforced(self):
        with self.assertRaises(ValidationError):
            ApprovalRequest.objects.create(
                division=self.division, entity_type="quotation", entity_id=uuid.uuid4(),
                approval_type="discount", requested_by=self.outsider,
            )
        with self.assertRaises(ValidationError):
            ApprovalRequest.objects.create(
                division=self.division, entity_type="quotation", entity_id=uuid.uuid4(),
                approval_type="discount", requested_by=self.staff, decided_by=self.outsider,
            )
        request = ApprovalRequest.objects.create(
            division=self.division, entity_type="quotation", entity_id=uuid.uuid4(),
            approval_type="discount", requested_by=self.staff, decided_by=self.staff,
        )
        self.assertEqual(request.pk, ApprovalRequest.objects.get(pk=request.pk).pk)

    def test_customer_communication_database_guards_reject_invalid_insert_and_update(self):
        now = timezone.now()
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_customercommunication "
                        "(id, customer_id, enquiry_id, division_id, channel, direction, occurred_at, summary, external_reference, recorded_by_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        [uuid.uuid4().hex, self.customer.pk.hex, self.other_enquiry.pk.hex,
                         self.division.pk.hex, "phone", "", now, "Invalid insert", "", self.staff.pk.hex],
                    )

        communication = CustomerCommunication.objects.create(
            customer=self.customer, enquiry=self.enquiry, division=self.division,
            channel=CustomerCommunication.Channel.PHONE,
            summary="Valid communication", recorded_by=self.staff,
        )
        for column, value in [
            ("recorded_by_id", self.outsider.pk.hex),
            ("enquiry_id", self.other_enquiry.pk.hex),
            ("customer_id", self.other_customer.pk.hex),
        ]:
            with self.subTest(operation="update", column=column):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f"UPDATE core_customercommunication SET {column} = %s WHERE id = %s",
                                [value, communication.pk.hex],
                            )

    def test_approval_request_database_guards_reject_invalid_insert_and_update(self):
        now = timezone.now()
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_approvalrequest "
                        "(id, created_at, updated_at, division_id, entity_type, entity_id, approval_type, status, "
                        "requested_by_id, decided_by_id, requested_at, decided_at, reason, decision_note, requested_value) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        [uuid.uuid4().hex, now, now, self.division.pk.hex, "quotation",
                         uuid.uuid4().hex, "discount", "pending", self.outsider.pk.hex,
                         None, now, None, "", "", None],
                    )

        request = ApprovalRequest.objects.create(
            division=self.division, entity_type="quotation", entity_id=uuid.uuid4(),
            approval_type="discount", requested_by=self.staff,
        )
        for column, value in [
            ("requested_by_id", self.outsider.pk.hex),
            ("decided_by_id", self.outsider.pk.hex),
        ]:
            with self.subTest(column=column):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f"UPDATE core_approvalrequest SET {column} = %s WHERE id = %s",
                                [value, request.pk.hex],
                            )
