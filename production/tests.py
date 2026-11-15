from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from sales.models import Customer, SalesOrder
from staff.models import StaffProfile
from .api import _job_visible, _visible_jobs
from .models import ProductionJob


class ProductionDepartmentAccessTests(TestCase):
    def setUp(self):
        self.creatives = Department.objects.create(code="creatives", name="SADACO Creatives")
        self.cnc = Department.objects.create(code="cnc", name="SADACO CNC")
        self.creative_manager = User.objects.create_user(username="creative_mgr", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.creative_manager, role=UserProfile.Role.MANAGER, department=self.creatives
        )
        self.cnc_manager = User.objects.create_user(username="cnc_mgr", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.cnc_manager, role=UserProfile.Role.MANAGER, department=self.cnc
        )
        creative_user = User.objects.create_user(username="creative_worker", password="StrongPass123!")
        UserProfile.objects.create(user=creative_user, role=UserProfile.Role.STAFF, department=self.creatives)
        cnc_user = User.objects.create_user(username="cnc_worker", password="StrongPass123!")
        UserProfile.objects.create(user=cnc_user, role=UserProfile.Role.STAFF, department=self.cnc)
        self.creative_staff = StaffProfile.objects.create(
            user=creative_user, staff_id="CRE-PROD-01", department=self.creatives
        )
        self.cnc_staff = StaffProfile.objects.create(
            user=cnc_user, staff_id="CNC-PROD-01", department=self.cnc
        )
        customer_a = Customer.objects.create(name="Creative Customer", phone="9000000001", department=self.creatives)
        customer_b = Customer.objects.create(name="CNC Customer", phone="9000000002", department=self.cnc)
        order_a = SalesOrder.objects.create(
            customer=customer_a, item_description="Creative order", quantity=1, confirmed_price=1000,
            responsible_staff=self.creative_staff,
        )
        order_b = SalesOrder.objects.create(
            customer=customer_b, item_description="CNC order", quantity=1, confirmed_price=2000,
            responsible_staff=self.cnc_staff,
        )
        self.creative_job = ProductionJob.objects.create(
            order=order_a, station=ProductionJob.Station.CUSTOM, assigned_staff=self.creative_staff
        )
        self.cnc_job = ProductionJob.objects.create(
            order=order_b, station=ProductionJob.Station.CNC, assigned_staff=self.cnc_staff
        )

    def test_manager_only_sees_jobs_from_own_department(self):
        visible_ids = set(_visible_jobs(self.creative_manager).values_list("id", flat=True))
        self.assertEqual(visible_ids, {self.creative_job.id})
        self.assertTrue(_job_visible(self.creative_manager, self.creative_job))
        self.assertFalse(_job_visible(self.creative_manager, self.cnc_job))

    def test_manager_without_department_sees_no_production_jobs(self):
        user = User.objects.create_user(username="unassigned_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=user, role=UserProfile.Role.MANAGER)
        self.assertFalse(_visible_jobs(user).exists())

    def test_super_admin_can_see_all_department_jobs(self):
        admin = User.objects.create_superuser(username="root", password="StrongPass123!")
        visible_ids = set(_visible_jobs(admin).values_list("id", flat=True))
        self.assertEqual(visible_ids, {self.creative_job.id, self.cnc_job.id})

    def test_assigned_staff_cannot_edit_production_job_configuration(self):
        self.client.force_login(self.creative_staff.user)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/update/",
            data='{"status":"completed"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.creative_job.refresh_from_db()
        self.assertNotEqual(self.creative_job.status, ProductionJob.Status.COMPLETED)
