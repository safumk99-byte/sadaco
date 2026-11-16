"""Regression tests for the approved SADACO PDF baseline data migrations.

These tests execute the RunPython seed functions against Django's test database.
The normal test-database setup also applies the complete migration graph, including
0013_staff_compensation_working_capacity.
"""
from decimal import Decimal
from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Department
from products.models import MachineRate, MaterialRateHistory, MaterialVariant, StaffCompensation
from staff.models import StaffProfile


def run_migration_function(module_path, function_name):
    migration_module = import_module(module_path)
    function = getattr(migration_module, function_name)
    # The seed functions use the historical app registry API. The current app
    # registry is compatible for these forward-only data assertions.
    function(apps, None)


class PdfBaselineMaterialSeedTests(TestCase):
    def test_material_and_machine_rates_match_approved_baseline(self):
        run_migration_function(
            "products.migrations.0010_material_master_and_costing_rates",
            "seed_material_master",
        )

        self.assertEqual(MaterialVariant.objects.count(), 51)
        self.assertEqual(MaterialRateHistory.objects.count(), 51)
        self.assertEqual(MachineRate.objects.count(), 5)

        self.assertEqual(
            MaterialVariant.objects.get(
                material_name="Acrylic Sheet", brand="Astari",
                thickness_mm=Decimal("1.80"), variant="441", colour="colour",
            ).purchase_rate,
            Decimal("3160.00"),
        )
        self.assertEqual(
            MaterialVariant.objects.get(
                material_name="Acrylic Sheet", brand="Astari",
                thickness_mm=Decimal("1.80"), variant="Others", colour="clear",
            ).purchase_rate,
            Decimal("2950.00"),
        )
        self.assertEqual(
            MaterialVariant.objects.get(
                material_name="Acrylic Sheet", brand="Otherbrand",
                thickness_mm=Decimal("8.00"), colour="colour",
            ).purchase_rate,
            Decimal("9728.00"),
        )
        self.assertEqual(
            MaterialVariant.objects.get(
                material_name="Indian Sheet", thickness_mm=Decimal("4.00"),
            ).purchase_rate,
            Decimal("796.00"),
        )
        self.assertEqual(
            MaterialVariant.objects.get(
                material_name="Mirror Sheet", variant="Brush Gold / Silver",
            ).purchase_rate,
            Decimal("640.00"),
        )

        self.assertFalse(MaterialVariant.objects.filter(
            material_name="Acrylic Sheet", brand="Astari",
            thickness_mm__in=[Decimal("6.50"), Decimal("7.50")],
        ).exists())
        self.assertFalse(MaterialVariant.objects.exclude(retail_rate__isnull=True).exists())

        machine_rates = set(
            MachineRate.objects.values_list("operation", "material_name", "thickness_mm", "rate", "unit")
        )
        self.assertEqual(machine_rates, {
            ("laser_cutting", "", None, Decimal("20.00"), "minute"),
            ("laser_engraving", "", None, Decimal("25.00"), "minute"),
            ("cnc_cutting", "Multy Wood", Decimal("5.00"), Decimal("50.00"), "sqft"),
            ("cnc_cutting", "Multy Wood", Decimal("6.00"), Decimal("50.00"), "sqft"),
            ("cnc_cutting", "Multy Wood", Decimal("8.00"), Decimal("60.00"), "sqft"),
        })

    def test_material_seed_is_repeatable_without_duplicate_rows(self):
        module = "products.migrations.0010_material_master_and_costing_rates"
        run_migration_function(module, "seed_material_master")
        first_material_ids = set(MaterialVariant.objects.values_list("id", flat=True))
        first_history_count = MaterialRateHistory.objects.count()
        first_machine_count = MachineRate.objects.count()

        run_migration_function(module, "seed_material_master")

        self.assertEqual(set(MaterialVariant.objects.values_list("id", flat=True)), first_material_ids)
        self.assertEqual(MaterialRateHistory.objects.count(), first_history_count)
        self.assertEqual(MachineRate.objects.count(), first_machine_count)


class PdfBaselineDepartmentAndCompensationTests(TestCase):
    def test_department_seed_is_idempotent(self):
        run_migration_function("core.migrations.0002_department", "seed_departments")
        run_migration_function("core.migrations.0002_department", "seed_departments")

        self.assertEqual(
            set(Department.objects.values_list("code", "name")),
            {
                ("creatives", "SADACO Creatives"),
                ("cnc", "SADACO CNC"),
                ("decor", "SADACO Decor Co."),
            },
        )
        self.assertEqual(Department.objects.count(), 3)

    def test_compensation_seed_only_assigns_existing_staff_profiles(self):
        monthly_staff = []
        for username in ("abdulbasith", "muhaimin"):
            user = User.objects.create_user(username=username)
            monthly_staff.append(StaffProfile.objects.create(user=user, staff_id=f"ST-{username}"))

        work_staff_user = User.objects.create_user(username="shibili")
        work_staff = StaffProfile.objects.create(user=work_staff_user, staff_id="ST-shibili")

        # Junaid and Ashiq have no StaffProfile here; the seed must not create
        # identities or compensation rows for people who are not in staff data.
        run_migration_function(
            "products.migrations.0011_seed_staff_compensation",
            "seed_staff_compensation",
        )

        self.assertEqual(StaffCompensation.objects.count(), 3)
        self.assertEqual(
            StaffCompensation.objects.get(staff=monthly_staff[0]).monthly_salary,
            Decimal("25000.00"),
        )
        self.assertEqual(
            StaffCompensation.objects.get(staff=monthly_staff[1]).monthly_salary,
            Decimal("15000.00"),
        )
        self.assertEqual(
            StaffCompensation.objects.get(staff=work_staff).payment_type,
            "per_work",
        )
        self.assertFalse(User.objects.filter(username__in=["junaid", "ashiq"]).exists())

    def test_capacity_fields_use_approved_defaults(self):
        user = User.objects.create_user(username="capacity_test")
        staff = StaffProfile.objects.create(user=user, staff_id="ST-CAPACITY")
        compensation = StaffCompensation.objects.create(
            staff=staff, payment_type="monthly", monthly_salary=Decimal("25000.00")
        )

        self.assertEqual(compensation.working_days_per_month, 26)
        self.assertEqual(compensation.productive_hours_per_day, Decimal("8.25"))
        self.assertEqual(compensation.monthly_productive_hours, Decimal("214.50"))
