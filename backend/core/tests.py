from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Customer, DesignRecord, DesignRevision, Division, Enquiry, JobCard,
    SalesOrder, StaffDivision, StaffProfile,
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
        self.assertEqual(response.status_code, 401)
