from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from .forms import ProductForm
from .models import Product, ProductCategory, StockTransaction


class ProductModuleTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.staff = User.objects.create_user(username="staff", password="StrongPass123!")
        UserProfile.objects.create(user=self.staff, role=UserProfile.Role.STAFF)
        self.category = ProductCategory.objects.create(name="General")

    def test_product_list_requires_login(self):
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 302)

    def test_manager_can_view_products(self):
        self.client.login(username="manager", password="StrongPass123!")
        response = self.client.get(reverse("products:list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_create_product(self):
        self.client.login(username="staff", password="StrongPass123!")
        response = self.client.get(reverse("products:create"))
        self.assertEqual(response.status_code, 403)

    def test_sku_is_normalized(self):
        form = ProductForm(data={
            "name": "Test Product", "sku": " ab-001 ",
            "category": self.category.pk, "description": "",
            "unit": "Piece", "selling_price": "100",
            "cost_price": "60", "stock_quantity": "10",
            "low_stock_threshold": "2", "status": "active",
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["sku"], "AB-001")

    def test_editing_product_with_inactive_category_remains_valid(self):
        category = ProductCategory.objects.create(name="Old Category", is_active=False)
        product = Product.objects.create(
            name="Existing Product", sku="OLD-001", category=category,
            selling_price=Decimal("100"), stock_quantity=Decimal("10"),
            low_stock_threshold=Decimal("2"),
        )
        form = ProductForm(instance=product, data={
            "name": "Existing Product", "sku": "OLD-001",
            "category": category.pk, "description": "",
            "unit": "Piece", "selling_price": "100",
            "cost_price": "60", "stock_quantity": "10",
            "low_stock_threshold": "2", "status": "active",
        })
        self.assertTrue(form.is_valid())

    def test_low_stock_property(self):
        product = Product.objects.create(
            name="Low Stock", sku="LOW-001", category=self.category,
            selling_price=Decimal("100"), stock_quantity=Decimal("2"),
            low_stock_threshold=Decimal("2"),
        )
        self.assertTrue(product.is_low_stock)


class InventoryModuleTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.manager = User.objects.create_user(username="inventory_manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.category = ProductCategory.objects.create(name="Inventory")
        self.product = Product.objects.create(
            name="Inventory Product", sku="INV-001", category=self.category,
            selling_price=Decimal("100"), cost_price=Decimal("50"),
            stock_quantity=Decimal("10"), low_stock_threshold=Decimal("2"),
        )

    def test_stock_in_updates_balance_and_creates_ledger(self):
        from .inventory import record_stock_transaction
        record = record_stock_transaction(
            product_id=self.product.pk,
            transaction_type=StockTransaction.TransactionType.IN,
            quantity=Decimal("5"),
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("15"))
        self.assertEqual(record.balance_after, Decimal("15"))

    def test_stock_out_cannot_make_balance_negative(self):
        from .inventory import record_stock_transaction
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            record_stock_transaction(
                product_id=self.product.pk,
                transaction_type=StockTransaction.TransactionType.OUT,
                quantity=Decimal("11"),
                user=self.manager,
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("10"))

    def test_adjustment_sets_exact_balance(self):
        from .inventory import record_stock_transaction
        record_stock_transaction(
            product_id=self.product.pk,
            transaction_type=StockTransaction.TransactionType.ADJUSTMENT,
            quantity=Decimal("7"),
            user=self.manager,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, Decimal("7"))

    def test_stock_page_requires_login(self):
        response = self.client.get(reverse("products:stock"))
        self.assertEqual(response.status_code, 302)

class MachineRateAuditAtomicityTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="machine_rate_auditor", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.create_url = "/api/costing/machine-rates/create/"

    def _post(self, url, payload):
        import json
        return self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )

    def test_machine_rate_create_writes_audit_log(self):
        from core.models import AuditLog
        from .models import MachineRate

        self.client.force_login(self.manager)
        response = self._post(self.create_url, {
            "operation": "laser_cutting",
            "material_name": "",
            "thickness_mm": "",
            "rate": "23.50",
            "unit": "minute",
            "is_active": True,
        })
        self.assertEqual(response.status_code, 201, response.content)
        rate = MachineRate.objects.get(pk=response.json()["id"])
        audit = AuditLog.objects.get(module="machine_rates", reference=f"MachineRate:{rate.pk}")
        self.assertEqual(audit.action, AuditLog.Action.CREATE)
        self.assertIn("rate=23.50/minute", audit.description)

    def test_machine_rate_update_audit_contains_previous_values(self):
        from core.models import AuditLog
        from .models import MachineRate

        rate = MachineRate.objects.create(
            operation=MachineRate.Operation.LASER_CUTTING,
            rate=Decimal("20.00"), unit="minute", is_active=True,
        )
        self.client.force_login(self.manager)
        response = self._post(
            f"/api/costing/machine-rates/{rate.pk}/update/",
            {"rate": "24.00", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.content)
        rate.refresh_from_db()
        self.assertEqual(rate.rate, Decimal("24.00"))
        self.assertFalse(rate.is_active)
        audit = AuditLog.objects.get(module="machine_rates", reference=f"MachineRate:{rate.pk}")
        self.assertEqual(audit.action, AuditLog.Action.UPDATE)
        self.assertIn("20.00", audit.description)
        self.assertIn("'is_active': True", audit.description)

    def test_audit_failure_rolls_back_machine_rate_change(self):
        from unittest.mock import patch
        from .models import MachineRate

        rate = MachineRate.objects.create(
            operation=MachineRate.Operation.LASER_CUTTING,
            rate=Decimal("20.00"), unit="minute", is_active=True,
        )
        self.client.force_login(self.manager)
        with patch("products.costing_api.AuditLog.objects.create", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self._post(
                    f"/api/costing/machine-rates/{rate.pk}/update/",
                    {"rate": "29.00"},
                )
        rate.refresh_from_db()
        self.assertEqual(rate.rate, Decimal("20.00"))


class MaterialAndCompensationAuditAtomicityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="costing_audit_admin", email="audit@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.admin)

    def _post(self, url, payload):
        import json
        return self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )

    def test_material_rate_history_failure_rolls_back_material_create(self):
        from unittest.mock import patch
        from products.models import MaterialVariant

        payload = {
            "material_name": "Atomic Acrylic",
            "brand": "Test",
            "thickness_mm": "3",
            "variant": "Clear",
            "colour": "clear",
            "sheet_width_ft": "8",
            "sheet_height_ft": "4",
            "purchase_rate": "3200",
            "retail_rate": "",
        }
        with patch(
            "products.models.MaterialRateHistory.objects.create",
            side_effect=RuntimeError("history unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self._post("/api/costing/materials/create/", payload)
        self.assertFalse(MaterialVariant.objects.filter(material_name="Atomic Acrylic").exists())

    def test_material_rate_update_history_failure_rolls_back_rate(self):
        from unittest.mock import patch
        from products.models import MaterialVariant

        material = MaterialVariant.objects.create(
            material_name="Atomic Existing", brand="Test", thickness_mm=Decimal("3"),
            colour="clear", purchase_rate=Decimal("3000"),
        )
        with patch(
            "products.models.MaterialRateHistory.objects.create",
            side_effect=RuntimeError("history unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self._post(
                    f"/api/costing/materials/{material.pk}/update/",
                    {"purchase_rate": "3500"},
                )
        material.refresh_from_db()
        self.assertEqual(material.purchase_rate, Decimal("3000"))

    def test_staff_compensation_audit_failure_rolls_back_salary_change(self):
        from unittest.mock import patch
        from staff.models import StaffProfile
        from products.models import StaffCompensation

        staff_user = User.objects.create_user(
            username="costed_staff", password="StrongPass123!"
        )
        staff = StaffProfile.objects.create(user=staff_user, staff_id="AUD-001")
        compensation = StaffCompensation.objects.create(
            staff=staff,
            payment_type=StaffCompensation.PaymentType.MONTHLY,
            monthly_salary=Decimal("15000"),
        )
        with patch(
            "products.costing_api.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                self._post(
                    f"/api/costing/staff-compensation/{staff.pk}/save/",
                    {
                        "payment_type": "monthly",
                        "monthly_salary": "18000",
                        "working_days_per_month": 26,
                        "productive_hours_per_day": "8.25",
                    },
                )
        compensation.refresh_from_db()
        self.assertEqual(compensation.monthly_salary, Decimal("15000"))
