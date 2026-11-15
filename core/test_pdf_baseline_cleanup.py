from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command, CommandError
from django.test import TestCase

from accounts.models import Notification, UserProfile
from core.management.commands import reset_to_pdf_baseline
from core.models import Department
from products.models import MachineRate, MaterialRateHistory, MaterialVariant, StaffCompensation
from sales.models import Customer
from staff.models import Designation, StaffProfile, WorkArea


class PdfBaselineCleanupCommandTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            code="cleanup-test", name="Cleanup Test Division"
        )
        self.user = User.objects.create_user(
            username="cleanup-identity", password="OriginalPassword123!"
        )
        self.user_profile = UserProfile.objects.create(
            user=self.user, role=UserProfile.Role.MANAGER, department=self.department
        )
        self.group = Group.objects.create(name="cleanup-preserved-group")
        self.user.groups.add(self.group)
        self.permission = Permission.objects.order_by("pk").first()
        if self.permission:
            self.group.permissions.add(self.permission)

        self.designation = Designation.objects.create(name="Cleanup Test Designation")
        self.work_area = WorkArea.objects.create(name="Cleanup Test Work Area")
        self.staff_profile = StaffProfile.objects.create(
            user=self.user,
            staff_id="CLEANUP-001",
            department=self.department,
            designation=self.designation,
            work_area=self.work_area,
        )

        self.customer = Customer.objects.create(
            name="Legacy Demo Customer", phone="9000000001", department=self.department
        )

        self.material = MaterialVariant.objects.create(
            material_name="Cleanup Test Acrylic",
            brand="Test Brand",
            variant="Test",
            purchase_rate=None,
            retail_rate=None,
        )
        self.rate_history = MaterialRateHistory.objects.create(
            material=self.material,
            purchase_rate="100.00",
            effective_from=date(2026, 11, 15),
            note="Authoritative baseline test record",
        )
        self.machine_rate = MachineRate.objects.create(
            operation=MachineRate.Operation.LASER_CUTTING,
            rate="20.00",
            unit="minute",
        )
        self.staff_compensation = StaffCompensation.objects.create(
            staff=self.staff_profile,
            payment_type=StaffCompensation.PaymentType.MONTHLY,
            monthly_salary="25000.00",
        )

    def run_command(self, apply=False):
        output = StringIO()
        args = {"stdout": output}
        if apply:
            args["apply"] = True
        with patch.object(reset_to_pdf_baseline.apps, "get_models", return_value=[Customer]):
            call_command("reset_to_pdf_baseline", **args)
        return output.getvalue()

    def protected_snapshot(self):
        return {
            "user": tuple(
                User.objects.filter(pk=self.user.pk).values_list(
                    "id", "username", "password", "is_active", "is_staff", "is_superuser"
                ).get()
            ),
            "user_profile": tuple(
                UserProfile.objects.filter(pk=self.user_profile.pk).values_list(
                    "id", "user_id", "role", "department_id", "is_active", "phone"
                ).get()
            ),
            "staff_profile": tuple(
                StaffProfile.objects.filter(pk=self.staff_profile.pk).values_list(
                    "id", "user_id", "staff_id", "department_id",
                    "designation_id", "work_area_id", "status", "notes"
                ).get()
            ),
            "group": Group.objects.filter(pk=self.group.pk).exists(),
            "permission_exists": (
                Permission.objects.filter(pk=self.permission.pk).exists()
                if self.permission else None
            ),
            "group_permission_link": (
                self.group.permissions.filter(pk=self.permission.pk).exists()
                if self.permission else None
            ),
            "department": Department.objects.filter(pk=self.department.pk).exists(),
            "designation": Designation.objects.filter(pk=self.designation.pk).exists(),
            "work_area": WorkArea.objects.filter(pk=self.work_area.pk).exists(),
            "material": MaterialVariant.objects.filter(pk=self.material.pk).exists(),
            "rate_history": MaterialRateHistory.objects.filter(pk=self.rate_history.pk).exists(),
            "machine_rate": MachineRate.objects.filter(pk=self.machine_rate.pk).exists(),
            "staff_compensation": StaffCompensation.objects.filter(
                pk=self.staff_compensation.pk
            ).exists(),
        }

    def test_default_run_is_dry_run(self):
        before = self.protected_snapshot()

        output = self.run_command()

        self.assertIn("DRY RUN ONLY", output)
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())
        self.assertEqual(before, self.protected_snapshot())

    def test_apply_deletes_eligible_customer_and_preserves_protected_records(self):
        before = self.protected_snapshot()

        output = self.run_command(apply=True)

        self.assertIn("Cleanup completed", output)
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())
        self.assertEqual(before, self.protected_snapshot())

    def test_collector_refuses_cascade_into_protected_user(self):
        notification = Notification.objects.create(
            user=self.user,
            title="Legacy notification",
            message="Must not cause user deletion",
        )
        output = StringIO()

        with patch.object(
            reset_to_pdf_baseline.apps, "get_models", return_value=[Notification]
        ):
            with self.assertRaises(CommandError):
                call_command("reset_to_pdf_baseline", apply=True, stdout=output)

        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.user_profile.pk).exists())
        self.assertTrue(StaffProfile.objects.filter(pk=self.staff_profile.pk).exists())
