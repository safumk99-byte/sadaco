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
        self.creatives = Department.objects.get_or_create(code="creatives", defaults={"name": "SADACO Creatives"})[0]
        self.cnc = Department.objects.get_or_create(code="cnc", defaults={"name": "SADACO CNC"})[0]
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


    def test_assigned_staff_cannot_finalize_job_through_progress_update(self):
        self.client.force_login(self.creative_staff.user)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"completed","progress_percent":100,"note":"Finished"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.creative_job.refresh_from_db()
        self.assertNotEqual(self.creative_job.status, ProductionJob.Status.COMPLETED)
        self.assertEqual(self.creative_job.progress_percent, 0)

    def test_manager_cannot_finalize_job_without_final_qc(self):
        self.client.force_login(self.creative_manager)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"completed","progress_percent":100,"note":"Attempted bypass"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.creative_job.refresh_from_db()
        self.assertNotEqual(self.creative_job.status, ProductionJob.Status.COMPLETED)
        self.assertEqual(self.creative_job.progress_percent, 0)

    def test_manager_cannot_set_completed_status_in_job_update_without_final_qc(self):
        self.client.force_login(self.creative_manager)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/update/",
            data='{"station":"custom","stage":"completed","status":"completed","priority":"normal","safety_checked":true,"design_checked":true,"material_ready":true}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.creative_job.refresh_from_db()
        self.assertNotEqual(self.creative_job.status, ProductionJob.Status.COMPLETED)

    def test_staff_cannot_mark_completed_stage_at_99_percent(self):
        self.client.force_login(self.creative_staff.user)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"completed","progress_percent":99,"note":"Attempted completion"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.creative_job.refresh_from_db()
        self.assertNotEqual(self.creative_job.stage, ProductionJob.Stage.COMPLETED)

    def test_manager_100_percent_requires_completed_stage(self):
        self.client.force_login(self.creative_manager)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"production","progress_percent":100,"note":"Incorrect final stage"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.creative_job.refresh_from_db()
        self.assertNotEqual(self.creative_job.status, ProductionJob.Status.COMPLETED)

    def test_manager_completed_stage_requires_100_percent(self):
        self.client.force_login(self.creative_manager)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"completed","progress_percent":99,"note":"Incomplete"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_progress_does_not_reopen_delivered_sales_order(self):
        from sales.models import SalesOrder
        self.creative_job.order.status = SalesOrder.Status.DELIVERED
        self.creative_job.order.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.creative_manager)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"production","progress_percent":50,"note":"Progress"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.creative_job.order.refresh_from_db()
        self.assertEqual(self.creative_job.order.status, SalesOrder.Status.DELIVERED)

    def test_progress_update_rejects_values_above_100(self):
        self.client.force_login(self.creative_staff.user)
        response = self.client.post(
            f"/api/production/jobs/{self.creative_job.pk}/progress/",
            data='{"stage":"production","progress_percent":150,"note":"Invalid"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.creative_job.refresh_from_db()
        self.assertEqual(self.creative_job.progress_percent, 0)

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


class ProductionMaterialFormSafetyTests(TestCase):
    def setUp(self):
        self.department = Department.objects.get_or_create(
            code="material-form-test", defaults={"name": "Material Form Test"}
        )[0]
        self.manager = User.objects.create_user(username="material_form_mgr", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager, role=UserProfile.Role.MANAGER, department=self.department
        )
        customer = Customer.objects.create(
            name="Material Form Customer", phone="9000000099", department=self.department
        )
        self.order = SalesOrder.objects.create(
            customer=customer, item_description="Material form job", quantity=1, confirmed_price=1000
        )
        self.job = ProductionJob.objects.create(order=self.order, station=ProductionJob.Station.LASER)

    def test_material_master_line_is_created_unissued_and_uses_master_unit(self):
        from decimal import Decimal
        from products.models import MaterialVariant
        material = MaterialVariant.objects.create(
            material_name="Acrylic Sheet", brand="Astari", thickness_mm=Decimal("3"),
            unit="Sheet",
        )
        self.client.force_login(self.manager)
        import json
        response = self.client.post(
            f"/api/production/jobs/{self.job.pk}/materials/",
            data=json.dumps({
                "material_variant": material.pk,
                "material_name": "Forged name must be replaced",
                "quantity_required": "2",
                "unit": "Piece",
                "issued_quantity": "2",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        from .models import ProductionMaterial
        line = ProductionMaterial.objects.get(job=self.job)
        self.assertEqual(line.material_variant_id, material.pk)
        self.assertEqual(line.material_name, "Acrylic Sheet")
        self.assertEqual(line.unit, "Sheet")
        self.assertEqual(line.issued_quantity, Decimal("0"))

    def test_material_line_rejects_both_product_and_material_master(self):
        from decimal import Decimal
        from products.models import Product, ProductCategory, MaterialVariant
        category = ProductCategory.objects.create(name="Material Form Test Category")
        product = Product.objects.create(name="Finished product", sku="PF-001", category=category, unit="Piece")
        material = MaterialVariant.objects.create(
            material_name="Acrylic Sheet", brand="Astari", thickness_mm=Decimal("3"), unit="Sheet",
        )
        self.client.force_login(self.manager)
        import json
        response = self.client.post(
            f"/api/production/jobs/{self.job.pk}/materials/",
            data=json.dumps({
                "product": product.pk, "material_variant": material.pk,
                "material_name": "Acrylic Sheet", "quantity_required": "2", "unit": "Sheet",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

class ProductionCostingTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from products.models import MachineRate, StaffCompensation, MaterialVariant
        from .models import ProductionMaterial

        self.department = Department.objects.get_or_create(
            code="costing-test", defaults={"name": "Costing Test"}
        )[0]
        self.other_department = Department.objects.get_or_create(
            code="costing-other", defaults={"name": "Costing Other"}
        )[0]
        self.manager = User.objects.create_user(username="costing_mgr", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager, role=UserProfile.Role.MANAGER, department=self.department
        )
        self.worker_user = User.objects.create_user(username="costing_worker", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.worker_user, role=UserProfile.Role.STAFF, department=self.department
        )
        self.worker = StaffProfile.objects.create(
            user=self.worker_user, staff_id="COST-001", department=self.department
        )
        StaffCompensation.objects.create(
            staff=self.worker, payment_type=StaffCompensation.PaymentType.MONTHLY,
            monthly_salary=Decimal("25000"), working_days_per_month=26,
            productive_hours_per_day=Decimal("8.25"),
        )
        customer = Customer.objects.create(
            name="Costing Customer", phone="9000000101", department=self.department
        )
        order = SalesOrder.objects.create(
            customer=customer, item_description="Costing job", quantity=1,
            confirmed_price=Decimal("1000"),
        )
        self.job = ProductionJob.objects.create(order=order, station=ProductionJob.Station.LASER)
        self.laser_rate = MachineRate.objects.create(
            operation=MachineRate.Operation.LASER_CUTTING, rate=Decimal("20"), unit="minute",
        )
        self.cnc_rate = MachineRate.objects.create(
            operation=MachineRate.Operation.CNC_CUTTING, material_name="Multy Wood",
            thickness_mm=Decimal("5"), rate=Decimal("50"), unit="sqft",
        )
        self.multywood = MaterialVariant.objects.create(
            material_name="Multy Wood", thickness_mm=Decimal("5"), unit="Sheet",
        )
        self.material_line = ProductionMaterial.objects.create(
            job=self.job, material_variant=self.multywood, material_name="Multy Wood",
            quantity_required=Decimal("2"), unit="Sheet",
        )
        self.other_user = User.objects.create_user(username="costing_other_worker", password="StrongPass123!")
        self.other_staff = StaffProfile.objects.create(
            user=self.other_user, staff_id="COST-OTHER", department=self.other_department,
        )

    def _post_cost(self, payload):
        import json
        self.client.force_login(self.manager)
        return self.client.post(
            f"/api/production/jobs/{self.job.pk}/cost-entries/",
            data=json.dumps(payload), content_type="application/json",
        )

    def test_machine_cost_uses_approved_rate_and_snapshots_amount(self):
        from decimal import Decimal
        from .models import ProductionCostEntry
        response = self._post_cost({
            "cost_type": "machine", "machine_rate": self.laser_rate.pk, "quantity": "12",
        })
        self.assertEqual(response.status_code, 201, response.content)
        entry = ProductionCostEntry.objects.get(pk=response.json()["id"])
        self.assertEqual(entry.unit, "minute")
        self.assertEqual(entry.unit_rate, Decimal("20.000000"))
        self.assertEqual(entry.total_cost, Decimal("240.00"))
        self.laser_rate.rate = Decimal("22")
        self.laser_rate.save(update_fields=["rate", "updated_at"])
        entry.refresh_from_db()
        self.assertEqual(entry.unit_rate, Decimal("20.000000"))
        self.assertEqual(entry.total_cost, Decimal("240.00"))

    def test_material_specific_cnc_rate_requires_matching_job_material(self):
        response = self._post_cost({
            "cost_type": "machine", "machine_rate": self.cnc_rate.pk,
            "material_line": self.material_line.pk, "quantity": "4.5",
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["unit"], "sqft")
        self.assertEqual(response.json()["total_cost"], "225.00")

    def test_cnc_rate_rejects_material_mismatch(self):
        from decimal import Decimal
        from products.models import MaterialVariant
        from .models import ProductionMaterial
        wrong = MaterialVariant.objects.create(
            material_name="Multy Wood", thickness_mm=Decimal("6"), unit="Sheet",
        )
        line = ProductionMaterial.objects.create(
            job=self.job, material_variant=wrong, material_name="Multy Wood",
            quantity_required=Decimal("1"), unit="Sheet",
        )
        response = self._post_cost({
            "cost_type": "machine", "machine_rate": self.cnc_rate.pk,
            "material_line": line.pk, "quantity": "1",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not match", response.json()["detail"])

    def test_monthly_labour_cost_uses_productive_hours_plan(self):
        from decimal import Decimal
        from .models import ProductionCostEntry
        response = self._post_cost({
            "cost_type": "labour", "staff": self.worker.pk, "quantity": "60",
        })
        self.assertEqual(response.status_code, 201, response.content)
        entry = ProductionCostEntry.objects.get(pk=response.json()["id"])
        expected_rate = (Decimal("25000") / Decimal("214.5") / Decimal("60")).quantize(Decimal("0.000001"))
        self.assertEqual(entry.unit, "minute")
        self.assertEqual(entry.unit_rate, expected_rate)
        self.assertEqual(entry.total_cost, Decimal("116.55"))
        self.assertEqual(entry.staff_name_snapshot, str(self.worker))

    def test_work_based_or_unconfigured_staff_rate_is_not_invented(self):
        from products.models import StaffCompensation
        StaffCompensation.objects.filter(staff=self.worker).update(
            payment_type=StaffCompensation.PaymentType.PER_WORK, monthly_salary=None,
        )
        response = self._post_cost({
            "cost_type": "labour", "staff": self.worker.pk, "quantity": "30",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Work-based rates are not configured", response.json()["detail"])

    def test_labour_staff_must_belong_to_job_department(self):
        response = self._post_cost({
            "cost_type": "labour", "staff": self.other_staff.pk, "quantity": "30",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("job's department", response.json()["detail"])

    def test_cost_entries_are_included_in_manager_job_cost_summary(self):
        self._post_cost({
            "cost_type": "machine", "machine_rate": self.laser_rate.pk, "quantity": "2",
        })
        self._post_cost({
            "cost_type": "labour", "staff": self.worker.pk, "quantity": "30",
        })
        self.client.force_login(self.manager)
        response = self.client.get(f"/api/production/jobs/{self.job.pk}/")
        self.assertEqual(response.status_code, 200, response.content)
        costs = response.json()["material_costs"]
        self.assertEqual(costs["machine_operation_cost"], "40.00")
        self.assertEqual(costs["direct_labour_cost"], "58.28")
        self.assertEqual(costs["total_conversion_cost"], "98.28")
        self.assertEqual(costs["total_tracked_job_cost"], "98.28")
        self.assertEqual(len(response.json()["cost_entries"]), 2)

    def test_non_manager_cannot_create_job_cost_entry(self):
        import json
        self.client.force_login(self.worker_user)
        response = self.client.post(
            f"/api/production/jobs/{self.job.pk}/cost-entries/",
            data=json.dumps({"cost_type": "machine", "machine_rate": self.laser_rate.pk, "quantity": "1"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
