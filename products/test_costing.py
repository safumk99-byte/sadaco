from decimal import Decimal
from django.test import TestCase

from .models import MaterialVariant, MachineRate, StaffCompensation
from accounts.models import UserProfile


class MaterialCostingModelTests(TestCase):
    def test_sheet_area_rate_is_calculated_from_purchase_rate(self):
        material = MaterialVariant.objects.create(
            material_name="Test Acrylic Sheet", brand="Test Brand",
            thickness_mm=Decimal("2.50"), colour="clear",
            sheet_width_ft=Decimal("8"), sheet_height_ft=Decimal("4"),
            purchase_rate=Decimal("3812.00"),
        )
        self.assertEqual(material.sheet_area_sqft, Decimal("32"))
        self.assertEqual(material.purchase_rate_sqft, Decimal("119.125"))

    def test_material_rate_changes_are_recorded_once_with_actor(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(username="rate-editor")
        material = MaterialVariant.objects.create(
            material_name="History Test Sheet", purchase_rate=Decimal("100.00")
        )
        self.assertEqual(material.rate_history.count(), 1)
        material.purchase_rate = Decimal("125.00")
        material._rate_changed_by = user
        material.save()
        self.assertEqual(material.rate_history.count(), 2)
        latest = material.rate_history.order_by("-pk").first()
        self.assertEqual(latest.purchase_rate, Decimal("125.00"))
        self.assertEqual(latest.changed_by, user)

    def test_new_unpriced_material_does_not_create_empty_rate_history(self):
        material = MaterialVariant.objects.create(material_name="Unpriced Test Sheet")
        self.assertEqual(material.rate_history.count(), 0)

    def test_missing_purchase_rate_keeps_sqft_rate_blank(self):
        material = MaterialVariant.objects.create(
            material_name="Test Indian Sheet", thickness_mm=Decimal("2"),
            sheet_width_ft=Decimal("4"), sheet_height_ft=Decimal("3"),
            purchase_rate=None,
        )
        self.assertIsNone(material.purchase_rate_sqft)

    def test_monthly_salary_hourly_cost_uses_documented_productive_hours(self):
        from django.contrib.auth import get_user_model
        from staff.models import StaffProfile
        user = get_user_model().objects.create_user(username="costing-test")
        staff = StaffProfile.objects.create(user=user, staff_id="COST-TEST")
        compensation = StaffCompensation.objects.create(
            staff=staff, payment_type="monthly", monthly_salary=Decimal("25000")
        )
        self.assertEqual(
            compensation.hourly_cost.quantize(Decimal("0.01")),
            Decimal("116.55"),
        )

    def test_machine_rate_supports_per_minute_and_per_sqft_units(self):
        laser = MachineRate.objects.create(operation="laser_cutting", rate=Decimal("20"), unit="minute")
        cnc = MachineRate.objects.create(
            operation="cnc_cutting", material_name="Multy Wood",
            thickness_mm=Decimal("8"), rate=Decimal("60"), unit="sqft",
        )
        self.assertEqual(laser.rate * 15, Decimal("300"))
        self.assertEqual(cnc.rate * 10, Decimal("600"))



class CostingPermissionTests(TestCase):
    def _user_with_role(self, username, role):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username=username, password="test-password")
        UserProfile.objects.create(user=user, role=role)
        return user

    def test_staff_cannot_read_costing_or_salary_rates(self):
        user = self._user_with_role("ordinary-staff", UserProfile.Role.STAFF)
        self.client.force_login(user)
        for endpoint in (
            "/api/costing/materials/",
            "/api/costing/machine-rates/",
            "/api/costing/staff/",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 403)

    def test_manager_can_read_costing_master_data(self):
        user = self._user_with_role("costing-manager", UserProfile.Role.MANAGER)
        self.client.force_login(user)
        for endpoint in (
            "/api/costing/materials/",
            "/api/costing/machine-rates/",
            "/api/costing/staff/",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 200)

    def test_inactive_manager_profile_cannot_read_costing_or_salary_rates(self):
        user = self._user_with_role("inactive-costing-manager", UserProfile.Role.MANAGER)
        user.profile.is_active = False
        user.profile.save(update_fields=["is_active"])
        self.client.force_login(user)
        for endpoint in (
            "/api/costing/materials/",
            "/api/costing/machine-rates/",
            "/api/costing/staff/",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 403)
