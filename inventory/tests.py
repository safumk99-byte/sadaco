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
        from purchase.models import Supplier, PurchaseOrder, PurchaseItem, GoodsReceipt, GoodsReceiptLine, MaterialStockLot
        supplier = Supplier.objects.create(name="Ledger Supplier")
        po = PurchaseOrder.objects.create(supplier=supplier, department=self.department)
        item = PurchaseItem.objects.create(
            purchase_order=po, material_variant=self.material,
            quantity=Decimal("10"), unit_cost=Decimal("100"),
        )
        receipt = GoodsReceipt.objects.create(purchase_order=po)
        receipt_line = GoodsReceiptLine.objects.create(
            receipt=receipt, purchase_item=item, received_quantity=Decimal("10"),
            unit_cost=Decimal("100"), line_total=Decimal("1000"),
        )
        self.lot = MaterialStockLot.objects.create(
            receipt_line=receipt_line, balance=self.balance,
            original_quantity=Decimal("10"), remaining_quantity=Decimal("10"),
            unit_cost=Decimal("100"),
        )

    def test_issue_updates_department_balance_and_job_line(self):
        issue, movement = issue_material(material_id=self.line.pk, quantity="3", lot_id=self.lot.pk, user=self.manager)
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("7"))
        self.assertEqual(self.line.issued_quantity, Decimal("3"))
        self.assertEqual(self.line.issue_unit_rate, Decimal("100"))
        self.assertEqual(movement.movement_type, MaterialStockMovement.Type.JOB_ISSUE)
        self.assertEqual(issue.quantity, Decimal("3"))

    def test_issue_rejects_insufficient_stock(self):
        with self.assertRaises(ValidationError):
            issue_material(material_id=self.line.pk, quantity="11", lot_id=self.lot.pk, user=self.manager)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("10"))

    def test_issue_requires_location_when_material_has_multiple_balances(self):
        MaterialStockBalance.objects.create(
            material=self.material, department=self.department, location="Secondary", quantity=Decimal("5")
        )
        with self.assertRaisesMessage(ValidationError, "Select the stock location"):
            issue_material(material_id=self.line.pk, quantity="1", lot_id=self.lot.pk, user=self.manager)

    def test_return_restores_stock_and_updates_returned_quantity(self):
        issue, _ = issue_material(material_id=self.line.pk, quantity="3", lot_id=self.lot.pk, user=self.manager)
        movement = return_issued_material(material_issue_id=issue.pk, quantity="1", user=self.manager)
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("8"))
        self.assertEqual(self.line.returned_quantity, Decimal("1"))
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.remaining_quantity, Decimal("8"))
        self.assertEqual(movement.source_issue_id, issue.pk)
        self.assertEqual(movement.movement_type, MaterialStockMovement.Type.RETURN)

    def test_wastage_does_not_deduct_issued_stock_twice(self):
        issue, _ = issue_material(material_id=self.line.pk, quantity="3", lot_id=self.lot.pk, user=self.manager)
        movement = record_issued_wastage(material_issue_id=issue.pk, quantity="1", user=self.manager)
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("7"))
        self.assertEqual(self.line.wastage_quantity, Decimal("1"))
        self.assertEqual(movement.balance_after, Decimal("7"))
        self.assertEqual(self.line.actual_consumption, Decimal("3"))
        self.assertEqual(movement.source_issue_id, issue.pk)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.remaining_quantity, Decimal("7"))

    def test_return_cannot_exceed_unreturned_issue(self):
        issue, _ = issue_material(material_id=self.line.pk, quantity="2", lot_id=self.lot.pk, user=self.manager)
        with self.assertRaises(ValidationError):
            return_issued_material(material_issue_id=issue.pk, quantity="3", user=self.manager)

    def test_return_restores_only_the_original_issue_lot(self):
        issue, _ = issue_material(material_id=self.line.pk, quantity="2", lot_id=self.lot.pk, user=self.manager)
        from purchase.models import MaterialStockLot
        other_balance = MaterialStockBalance.objects.create(
            material=self.material, department=self.department, location="Other Store", quantity=0
        )
        from purchase.models import GoodsReceipt, GoodsReceiptLine
        receipt = GoodsReceipt.objects.create(purchase_order=issue.stock_lot.receipt_line.receipt.purchase_order)
        receipt_line = GoodsReceiptLine.objects.create(
            receipt=receipt, purchase_item=issue.stock_lot.receipt_line.purchase_item,
            received_quantity=Decimal("2"), unit_cost=Decimal("100"), line_total=Decimal("200"),
        )
        other_lot = MaterialStockLot.objects.create(
            receipt_line=receipt_line, balance=other_balance,
            original_quantity=Decimal("2"), remaining_quantity=Decimal("2"), unit_cost=Decimal("100")
        )
        # A tampered issue-to-lot relationship must fail the job-department/location consistency check.
        issue.stock_lot = other_lot
        issue.save(update_fields=["stock_lot"])
        with self.assertRaises(MaterialStockBalance.DoesNotExist):
            return_issued_material(material_issue_id=issue.pk, quantity="1", user=self.manager)

    def test_return_and_wastage_cannot_exceed_the_same_issue(self):
        issue, _ = issue_material(material_id=self.line.pk, quantity="3", lot_id=self.lot.pk, user=self.manager)
        return_issued_material(material_issue_id=issue.pk, quantity="1", user=self.manager)
        record_issued_wastage(material_issue_id=issue.pk, quantity="2", user=self.manager)
        with self.assertRaises(ValidationError):
            record_issued_wastage(material_issue_id=issue.pk, quantity="0.01", user=self.manager)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.remaining_quantity, Decimal("8"))



from inventory.models import MaterialStockCount
from inventory.services import submit_material_stock_count, review_material_stock_count


class MaterialStockCountTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="count-a", name="Count A")
        self.admin = User.objects.create_superuser(username="count-admin", password="StrongPass123!")
        self.manager = User.objects.create_user(username="count-manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        material = MaterialVariant.objects.create(material_name="Count Sheet", purchase_rate=Decimal("200"))
        self.balance = MaterialStockBalance.objects.create(
            material=material, department=self.department, location="Store 1", quantity=Decimal("12")
        )

    def test_count_submission_does_not_change_stock_until_approval(self):
        count = submit_material_stock_count(
            balance_id=self.balance.pk, counted_quantity="10", user=self.manager, reason="Physical count"
        )
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("12"))
        self.assertEqual(count.variance, Decimal("-2"))
        self.assertEqual(count.status, MaterialStockCount.Status.PENDING)

    def test_approval_applies_variance_and_writes_correction_movement(self):
        count = submit_material_stock_count(balance_id=self.balance.pk, counted_quantity="10", user=self.manager)
        reviewed = review_material_stock_count(count_id=count.pk, approve=True, user=self.admin)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("10"))
        self.assertEqual(reviewed.status, MaterialStockCount.Status.APPROVED)
        self.assertEqual(reviewed.correction_movement.movement_type, MaterialStockMovement.Type.CORRECTION)
        self.assertEqual(reviewed.correction_movement.quantity, Decimal("2"))

    def test_reject_does_not_change_stock(self):
        count = submit_material_stock_count(balance_id=self.balance.pk, counted_quantity="15", user=self.manager)
        reviewed = review_material_stock_count(count_id=count.pk, approve=False, user=self.admin)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("12"))
        self.assertEqual(reviewed.status, MaterialStockCount.Status.REJECTED)

    def test_stale_count_cannot_be_approved(self):
        count = submit_material_stock_count(balance_id=self.balance.pk, counted_quantity="10", user=self.manager)
        self.balance.quantity = Decimal("11")
        self.balance.save(update_fields=["quantity", "updated_at"])
        with self.assertRaisesMessage(ValidationError, "Stock changed after this count"):
            review_material_stock_count(count_id=count.pk, approve=True, user=self.admin)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("11"))
