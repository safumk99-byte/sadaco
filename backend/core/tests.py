from decimal import Decimal
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    ApprovalRequest, Customer, CustomerCommunication, DesignRecord, DesignRevision, Division, Enquiry, FollowUp, JobCard, OrderStatusEvent, Quotation,
    OrderAssignment, ProductionStage, ProductionUpdate, SalesOrder, StaffDivision,
    StaffProfile, StaffTask, TaskUpdate, StoredFile, DesignRevisionFile, Role, StaffRole, Department, StaffDepartment,
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
        designer_role = Role.objects.create(code="designer", name="Designer")
        StaffRole.objects.create(staff=self.designer, role=designer_role, division=self.division)
        customer = Customer.objects.create(customer_code="APR-API-001", display_name="API Approval Customer")
        order = SalesOrder.objects.create(
            order_number="SAD-APPROVAL-API-001", customer=customer, division=self.division,
            created_by=self.manager, subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(
            sales_order=order, title="API Approval Artwork", assigned_to=self.designer
        )
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


    def test_unassigned_same_division_staff_cannot_read_design_revision(self):
        outsider_user = get_user_model().objects.create_user(
            username="approval-api-same-division-outsider", password="password123"
        )
        outsider = StaffProfile.objects.create(
            user=outsider_user, display_name="Unassigned Same Division Staff"
        )
        StaffDivision.objects.create(staff=outsider, division=self.division)
        self.client.force_authenticate(outsider_user)
        response = self.client.get(f"/api/design-revisions/{self.revision.pk}/")
        self.assertEqual(response.status_code, 404)



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



class OrderTaskActorScopeTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(code="order-task-scope", name="Order Task Scope")
        self.other_division = Division.objects.create(code="order-task-other", name="Order Task Other")
        User = get_user_model()
        user = User.objects.create_user(username="order-task-member", password="test-password-123")
        self.staff = StaffProfile.objects.create(user=user, display_name="Order Task Member")
        StaffDivision.objects.create(staff=self.staff, division=self.division)
        other_user = User.objects.create_user(username="order-task-outsider", password="test-password-123")
        self.outsider = StaffProfile.objects.create(user=other_user, display_name="Order Task Outsider")
        StaffDivision.objects.create(staff=self.outsider, division=self.other_division)
        customer = Customer.objects.create(
            customer_code="ORDER-TASK-CUSTOMER", display_name="Order Task Customer"
        )
        self.order = SalesOrder.objects.create(
            order_number="ORDER-TASK-SCOPE-001", customer=customer,
            division=self.division, created_by=self.staff,
        )
        self.task = StaffTask.objects.create(
            task_number="ORDER-TASK-SCOPE-001", division=self.division,
            sales_order=self.order, assigned_to=self.staff, assigned_by=self.staff,
            title="Scope test task", priority="normal",
        )

    def test_order_status_event_model_scope_is_enforced(self):
        with self.assertRaises(ValidationError):
            OrderStatusEvent.objects.create(
                sales_order=self.order, to_status="production", changed_by=self.outsider,
            )
        event = OrderStatusEvent.objects.create(
            sales_order=self.order, to_status="production", changed_by=self.staff,
        )
        self.assertEqual(event.sales_order_id, self.order.pk)

    def test_task_update_model_scope_is_enforced(self):
        with self.assertRaises(ValidationError):
            TaskUpdate.objects.create(
                staff_task=self.task, reported_by=self.outsider,
                update_type=TaskUpdate.UpdateType.PROGRESS, note="Out of division",
            )
        update = TaskUpdate.objects.create(
            staff_task=self.task, reported_by=self.staff,
            update_type=TaskUpdate.UpdateType.PROGRESS, note="Valid update",
        )
        self.assertEqual(update.staff_task_id, self.task.pk)

    def test_order_status_event_database_guard_rejects_invalid_insert_and_update(self):
        now = timezone.now()
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_orderstatusevent "
                        "(id, sales_order_id, from_status, to_status, changed_by_id, changed_at, reason) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        [uuid.uuid4().hex, self.order.pk.hex, "", "production",
                         self.outsider.pk.hex, now, "Invalid actor"],
                    )
        event = OrderStatusEvent.objects.create(
            sales_order=self.order, to_status="production", changed_by=self.staff,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_orderstatusevent SET changed_by_id = %s WHERE id = %s",
                        [self.outsider.pk.hex, event.pk.hex],
                    )

    def test_task_update_database_guard_rejects_invalid_insert_and_update(self):
        now = timezone.now()
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_taskupdate "
                        "(id, staff_task_id, reported_by_id, update_type, note, evidence_file_id, recorded_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        [uuid.uuid4().hex, self.task.pk.hex, self.outsider.pk.hex,
                         "progress", "Invalid reporter", None, now],
                    )
        update = TaskUpdate.objects.create(
            staff_task=self.task, reported_by=self.staff,
            update_type=TaskUpdate.UpdateType.PROGRESS, note="Valid update",
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_taskupdate SET reported_by_id = %s WHERE id = %s",
                        [self.outsider.pk.hex, update.pk.hex],
                    )



class DepartmentRoleScopeTests(TestCase):
    def setUp(self):
        from .models import Department
        self.division_a = Division.objects.create(
            code="role-scope-a", name="Role Scope Division A"
        )
        self.division_b = Division.objects.create(
            code="role-scope-b", name="Role Scope Division B"
        )
        self.department_a = Department.objects.create(
            division=self.division_a, name="Design"
        )
        self.department_b = Department.objects.create(
            division=self.division_b, name="Design"
        )
        user = get_user_model().objects.create_user(
            username="department-role-user", password="test-password-123"
        )
        self.staff = StaffProfile.objects.create(
            user=user, display_name="Department Role User"
        )
        self.manager_role = Role.objects.create(
            code="manager", name="Manager"
        )

    def test_department_scoped_manager_is_limited_to_its_department_division(self):
        from .permissions import active_role_division_ids, has_active_role

        StaffRole.objects.create(
            staff=self.staff,
            role=self.manager_role,
            department=self.department_a,
        )

        self.assertTrue(
            has_active_role(self.staff, "manager", division_id=self.division_a.pk)
        )
        self.assertFalse(
            has_active_role(self.staff, "manager", division_id=self.division_b.pk)
        )
        self.assertEqual(
            active_role_division_ids(self.staff, "manager"),
            [self.division_a.pk],
        )


    def test_staff_role_rejects_department_from_another_division(self):
        with self.assertRaises(ValidationError):
            StaffRole.objects.create(
                staff=self.staff,
                role=self.manager_role,
                division=self.division_a,
                department=self.department_b,
            )

    def test_staff_role_database_guard_rejects_mismatched_department_insert_and_update(self):
        now = timezone.now()
        invalid_id = uuid.uuid4()
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_staffrole "
                        "(id, created_at, updated_at, staff_id, role_id, division_id, "
                        "department_id, valid_from, valid_until, granted_by_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        [
                            invalid_id, now, now, self.staff.pk, self.manager_role.pk,
                            self.division_a.pk, self.department_b.pk, now, None, None,
                        ],
                    )

        assignment = StaffRole.objects.create(
            staff=self.staff,
            role=self.manager_role,
            division=self.division_a,
            department=self.department_a,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_staffrole SET division_id = %s WHERE id = %s",
                        [self.division_b.pk, assignment.pk],
                    )



class DesignApprovalActorScopeTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(
            code="approval-scope", name="Approval Scope Division"
        )
        manager_user = get_user_model().objects.create_user(
            username="approval-scope-manager", password="test-password-123"
        )
        outsider_user = get_user_model().objects.create_user(
            username="approval-scope-outsider", password="test-password-123"
        )
        self.manager = StaffProfile.objects.create(
            user=manager_user, display_name="Approval Scope Manager"
        )
        self.outsider = StaffProfile.objects.create(
            user=outsider_user, display_name="Approval Scope Outsider"
        )
        StaffDivision.objects.create(staff=self.manager, division=self.division)
        manager_role = Role.objects.create(code="manager", name="Manager")
        StaffRole.objects.create(
            staff=self.manager, role=manager_role, division=self.division
        )
        customer = Customer.objects.create(
            customer_code="APPROVAL-SCOPE-C", display_name="Approval Scope Customer"
        )
        order = SalesOrder.objects.create(
            order_number="APPROVAL-SCOPE-O", customer=customer,
            division=self.division, created_by=self.manager,
            subtotal=Decimal("100"), grand_total=Decimal("100"),
            balance_due=Decimal("100"),
        )
        design = DesignRecord.objects.create(
            sales_order=order, title="Approval Scope Design"
        )
        self.revision = DesignRevision.objects.create(
            design_record=design, revision_number=1,
            status="pending", created_by=self.manager,
        )

    def test_model_rejects_approval_by_staff_without_manager_or_global_founder_role(self):
        from .models import DesignApproval

        with self.assertRaises(ValidationError):
            DesignApproval.objects.create(
                design_revision=self.revision,
                reviewer_type="customer",
                decision="approved",
                reviewed_by=self.outsider,
                reviewed_at=timezone.now(),
            )

    def test_model_requires_customer_approval_before_manager_approval(self):
        from .models import DesignApproval

        with self.assertRaises(ValidationError):
            DesignApproval.objects.create(
                design_revision=self.revision,
                reviewer_type="manager",
                decision="approved",
                reviewed_by=self.manager,
                reviewed_at=timezone.now(),
            )

    def test_database_guard_rejects_unauthorized_actor_and_manager_approval_out_of_order(self):
        now = timezone.now()
        from .models import DesignApproval

        cases = [
            (self.outsider, "customer", "approved"),
            (self.manager, "manager", "approved"),
            (self.manager, "unexpected", "approved"),
        ]
        for actor, reviewer_type, decision in cases:
            with self.subTest(actor=actor.display_name, reviewer_type=reviewer_type):
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO core_designapproval "
                                "(id, design_revision_id, reviewer_type, decision, "
                                "reviewed_by_id, reviewed_at, comments) "
                                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                [
                                    uuid.uuid4().hex, self.revision.pk.hex, reviewer_type,
                                    decision, actor.pk.hex, now, "Raw SQL bypass attempt",
                                ],
                            )

    def test_service_records_customer_then_manager_approval(self):
        from .services import record_design_approval

        customer_approval = record_design_approval(
            revision_id=self.revision.pk,
            reviewer_type="customer",
            decision="approved",
            actor=self.manager,
        )
        manager_approval = record_design_approval(
            revision_id=self.revision.pk,
            reviewer_type="manager",
            decision="approved",
            actor=self.manager,
        )

        self.assertEqual(customer_approval.reviewer_type, "customer")
        self.assertEqual(manager_approval.reviewer_type, "manager")
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.status, "approved")
        self.assertIsNotNone(self.revision.locked_at)



class AuditEventImmutabilityTests(TestCase):
    def setUp(self):
        from .models import AuditEvent

        self.event = AuditEvent.objects.create(
            entity_type="test_entity",
            entity_id=uuid.uuid4(),
            action="created",
            after_data={"status": "new"},
        )

    def test_model_rejects_audit_event_update_and_delete(self):
        from .models import AuditEvent

        self.event.action = "tampered"
        with self.assertRaises(ValidationError):
            self.event.save()
        with self.assertRaises(ValidationError):
            self.event.delete()
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=self.event.pk).update(action="tampered")
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=self.event.pk).delete()

    def test_database_rejects_raw_sql_audit_event_update_and_delete(self):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_auditevent SET action = %s WHERE id = %s",
                        ["tampered", self.event.pk.hex],
                    )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM core_auditevent WHERE id = %s",
                        [self.event.pk.hex],
                    )



class DepartmentDivisionImmutabilityTests(TestCase):
    def setUp(self):
        self.division_a = Division.objects.create(
            code="dept-lock-a", name="Department Lock Division A"
        )
        self.division_b = Division.objects.create(
            code="dept-lock-b", name="Department Lock Division B"
        )
        self.department = Department.objects.create(
            division=self.division_a, name="Linked Department"
        )
        user = get_user_model().objects.create_user(
            username="department-lock-staff", password="test-password-123"
        )
        self.staff = StaffProfile.objects.create(
            user=user, display_name="Department Lock Staff"
        )

    def test_department_model_rejects_division_change_when_staff_role_exists(self):
        role = Role.objects.create(code="dept-lock-manager", name="Department Manager")
        StaffRole.objects.create(
            staff=self.staff,
            role=role,
            department=self.department,
        )
        self.department.division = self.division_b
        with self.assertRaises(ValidationError):
            self.department.save()

    def test_department_model_rejects_division_change_when_staff_membership_exists(self):
        StaffDepartment.objects.create(
            staff=self.staff,
            department=self.department,
        )
        self.department.division = self.division_b
        with self.assertRaises(ValidationError):
            self.department.save()

    def test_database_guard_rejects_division_change_with_staff_role_link(self):
        role = Role.objects.create(code="dept-lock-db-role", name="Department DB Role")
        StaffRole.objects.create(
            staff=self.staff,
            role=role,
            department=self.department,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_department SET division_id = %s WHERE id = %s",
                        [self.division_b.pk.hex, self.department.pk.hex],
                    )

    def test_database_guard_rejects_division_change_with_staff_membership_link(self):
        StaffDepartment.objects.create(
            staff=self.staff,
            department=self.department,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_department SET division_id = %s WHERE id = %s",
                        [self.division_b.pk.hex, self.department.pk.hex],
                    )


class ActiveStaffReferenceGuardTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(
            code="active-staff-guard", name="Active Staff Guard Division"
        )
        User = get_user_model()
        active_user = User.objects.create_user(
            username="active-staff-guard-user", password="test-password-123"
        )
        self.active_staff = StaffProfile.objects.create(
            user=active_user, display_name="Active Guard Staff"
        )
        StaffDivision.objects.create(staff=self.active_staff, division=self.division)

        inactive_user = User.objects.create_user(
            username="inactive-staff-guard-user", password="test-password-123"
        )
        self.inactive_staff = StaffProfile.objects.create(
            user=inactive_user,
            display_name="Inactive Guard Staff",
            employment_status=StaffProfile.EmploymentStatus.INACTIVE,
        )
        self.customer = Customer.objects.create(
            customer_code="ACTIVE-GUARD-CUSTOMER",
            display_name="Active Guard Customer",
        )
        self.enquiry = Enquiry.objects.create(
            enquiry_number="ACTIVE-GUARD-ENQUIRY",
            customer=self.customer,
            division=self.division,
            source=Enquiry.Source.DIRECT,
            requested_product_service="Test service",
            created_by=self.active_staff,
        )
        self.communication = CustomerCommunication.objects.create(
            customer=self.customer,
            enquiry=self.enquiry,
            division=self.division,
            channel=CustomerCommunication.Channel.PHONE,
            summary="Initial active-staff communication",
            recorded_by=self.active_staff,
        )

    def test_model_validation_rejects_inactive_staff_as_creator_assignee_and_actor(self):
        with self.assertRaises(ValidationError):
            Enquiry.objects.create(
                enquiry_number="INACTIVE-GUARD-ENQUIRY",
                customer=self.customer,
                division=self.division,
                source=Enquiry.Source.DIRECT,
                requested_product_service="Should be rejected",
                created_by=self.inactive_staff,
            )

        with self.assertRaises(ValidationError):
            Enquiry.objects.create(
                enquiry_number="INACTIVE-GUARD-ASSIGNEE",
                customer=self.customer,
                division=self.division,
                source=Enquiry.Source.DIRECT,
                requested_product_service="Should be rejected",
                assigned_to=self.inactive_staff,
                created_by=self.active_staff,
            )

        with self.assertRaises(ValidationError):
            CustomerCommunication.objects.create(
                customer=self.customer,
                enquiry=self.enquiry,
                division=self.division,
                channel=CustomerCommunication.Channel.PHONE,
                summary="Inactive actor",
                recorded_by=self.inactive_staff,
            )

        with self.assertRaises(ValidationError):
            ApprovalRequest.objects.create(
                division=self.division,
                entity_type="enquiry",
                entity_id=self.enquiry.pk,
                approval_type="test",
                requested_by=self.inactive_staff,
            )

    def test_crm_api_rejects_inactive_assignees_with_validation_response(self):
        client = APIClient()
        client.force_authenticate(self.active_staff.user)
        enquiry_response = client.post(
            "/api/enquiries/",
            {
                "enquiry_number": "INACTIVE-API-ASSIGNEE",
                "customer": str(self.customer.pk),
                "division": str(self.division.pk),
                "source": Enquiry.Source.DIRECT,
                "requested_product_service": "Inactive assignee test",
                "assigned_to": str(self.inactive_staff.pk),
            },
            format="json",
        )
        self.assertEqual(enquiry_response.status_code, 400)
        self.assertIn("assigned_to", enquiry_response.data)

        follow_up_response = client.post(
            "/api/follow-ups/",
            {
                "enquiry": str(self.enquiry.pk),
                "assigned_to": str(self.inactive_staff.pk),
                "due_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(follow_up_response.status_code, 400)
        self.assertIn("assigned_to", follow_up_response.data)

    def test_global_founder_role_does_not_restore_access_for_inactive_staff(self):
        founder_role = Role.objects.create(code="founder", name="Founder")
        self.inactive_staff.employment_status = StaffProfile.EmploymentStatus.ACTIVE
        self.inactive_staff.save()
        StaffRole.objects.create(staff=self.inactive_staff, role=founder_role)
        self.inactive_staff.employment_status = StaffProfile.EmploymentStatus.INACTIVE
        self.inactive_staff.save(update_fields=["employment_status"])

        from .models import staff_has_division_access
        from .permissions import is_founder
        self.assertFalse(
            staff_has_division_access(self.inactive_staff.pk, self.division.pk)
        )
        self.assertFalse(is_founder(self.inactive_staff))

    def test_database_guards_reject_inactive_staff_references_on_insert_and_update(self):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_enquiry SET created_by_id = %s WHERE id = %s",
                        [self.inactive_staff.pk.hex, self.enquiry.pk.hex],
                    )

        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE core_customercommunication SET recorded_by_id = %s WHERE id = %s",
                        [self.inactive_staff.pk.hex, self.communication.pk.hex],
                    )

        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO core_staffdivision (id, staff_id, division_id) "
                        "VALUES (%s, %s, %s)",
                        [
                            uuid.uuid4().hex,
                            self.inactive_staff.pk.hex,
                            self.division.pk.hex,
                        ],
                    )
