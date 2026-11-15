from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from inventory.models import MaterialStockBalance, MaterialStockMovement
from inventory.services import issue_material, return_issued_material, record_issued_wastage
from products.models import MaterialVariant
from production.models import ProductionJob, ProductionMaterial
from sales.models import Customer, SalesOrder


class MaterialLedgerWorkflowTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="ledger-a", name="Ledger A")
        self.other_department = Department.objects.create(code="ledger-b", name="Ledger B")
        self.manager = User.objects.create_user(username="ledger-manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.customer = Customer.objects.create(name="Ledger Customer", phone="9000000001", department=self.department)
        self.order = SalesOrder.objects.create(
            customer=self.customer, item_description="Test job", quantity=1,
            confirmed_price=Decimal("1000"),
        )
        self.job = ProductionJob.objects.create(order=self.order, station=ProductionJob.Station.LASER)
        self.material = MaterialVariant.objects.create(
            material_name="Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("100"), unit="Sheet",
        )
        self.balance = MaterialStockBalance.objects.create(
            material=self.material, department=self.department, location="Main Store",
            quantity=Decimal("10"),
        )
        self.line = ProductionMaterial.objects.create(
            job=self.job, material_variant=self.material, material_name="Acrylic",
            quantity_required=Decimal("5"), unit="Sheet",
        )

    def test_issue_updates_department_balance_and_job_line(self):
        issue, movement = issue_material(material_id=self.line.pk, quantity="3", user=self.manager)
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("7"))
        self.assertEqual(self.line.issued_quantity, Decimal("3"))
        self.assertEqual(self.line.issue_unit_rate, Decimal("100"))
        self.assertEqual(movement.movement_type, MaterialStockMovement.Type.JOB_ISSUE)
        self.assertEqual(issue.quantity, Decimal("3"))

    def test_issue_rejects_insufficient_stock(self):
        with self.assertRaises(ValidationError):
            issue_material(material_id=self.line.pk, quantity="11", user=self.manager)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("10"))

    def test_issue_requires_location_when_material_has_multiple_balances(self):
        MaterialStockBalance.objects.create(
            material=self.material, department=self.department, location="Secondary", quantity=Decimal("5")
        )
        with self.assertRaisesMessage(ValidationError, "Select the stock location"):
            issue_material(material_id=self.line.pk, quantity="1", user=self.manager)

    def test_return_restores_stock_and_updates_returned_quantity(self):
        issue_material(material_id=self.line.pk, quantity="3", user=self.manager)
        movement = return_issued_material(material_id=self.line.pk, quantity="1", balance_id=self.balance.pk, user=self.manager)
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("8"))
        self.assertEqual(self.line.returned_quantity, Decimal("1"))
        self.assertEqual(movement.movement_type, MaterialStockMovement.Type.RETURN)

    def test_wastage_does_not_deduct_issued_stock_twice(self):
        issue_material(material_id=self.line.pk, quantity="3", user=self.manager)
        movement = record_issued_wastage(material_id=self.line.pk, quantity="1", balance_id=self.balance.pk, user=self.manager)
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("7"))
        self.assertEqual(self.line.wastage_quantity, Decimal("1"))
        self.assertEqual(movement.balance_after, Decimal("7"))
        self.assertEqual(self.line.actual_consumption, Decimal("3"))

    def test_return_cannot_exceed_unreturned_issue(self):
        issue_material(material_id=self.line.pk, quantity="2", user=self.manager)
        with self.assertRaises(ValidationError):
            return_issued_material(material_id=self.line.pk, quantity="3", balance_id=self.balance.pk, user=self.manager)

    def test_foreign_department_balance_cannot_receive_return(self):
        issue_material(material_id=self.line.pk, quantity="2", user=self.manager)
        foreign = MaterialStockBalance.objects.create(
            material=self.material, department=self.other_department, location="Other Store", quantity=0
        )
        with self.assertRaises(MaterialStockBalance.DoesNotExist):
            return_issued_material(material_id=self.line.pk, quantity="1", balance_id=foreign.pk, user=self.manager)
