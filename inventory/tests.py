import json
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
from purchase.models import MaterialStockLot


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

    def test_stock_reconciliation_matches_movement_and_receipt_lot_after_issue_and_wastage(self):
        from inventory.services import reconcile_material_stock_balance

        MaterialStockMovement.objects.create(
            balance=self.balance, movement_type=MaterialStockMovement.Type.OPENING,
            quantity=Decimal("10"), balance_after=Decimal("10"), reference="OPENING-TEST",
        )
        issue, _ = issue_material(
            material_id=self.line.pk, quantity="3", lot_id=self.lot.pk, user=self.manager,
        )
        record_issued_wastage(
            material_issue_id=issue.pk, quantity="1", user=self.manager,
        )

        self.balance.refresh_from_db()
        self.lot.refresh_from_db()
        result = reconcile_material_stock_balance(self.balance)

        self.assertEqual(self.balance.quantity, Decimal("7"))
        self.assertEqual(self.lot.remaining_quantity, Decimal("7"))
        self.assertEqual(result["movement_expected_balance"], "7.000")
        self.assertEqual(result["receipt_lot_remaining"], "7.000")
        self.assertEqual(result["unbatched_quantity"], "0.000")
        self.assertTrue(result["reconciled"])
        self.assertFalse(result["unbatched_warning"])

    def test_stock_reconciliation_matches_after_issue_and_return(self):
        from inventory.services import reconcile_material_stock_balance

        MaterialStockMovement.objects.create(
            balance=self.balance, movement_type=MaterialStockMovement.Type.OPENING,
            quantity=Decimal("10"), balance_after=Decimal("10"), reference="OPENING-RETURN-TEST",
        )
        issue, _ = issue_material(
            material_id=self.line.pk, quantity="3", lot_id=self.lot.pk, user=self.manager,
        )
        return_issued_material(
            material_issue_id=issue.pk, quantity="1", user=self.manager,
        )

        self.balance.refresh_from_db()
        self.lot.refresh_from_db()
        result = reconcile_material_stock_balance(self.balance)

        self.assertEqual(self.balance.quantity, Decimal("8"))
        self.assertEqual(self.lot.remaining_quantity, Decimal("8"))
        self.assertEqual(result["movement_expected_balance"], "8.000")
        self.assertEqual(result["movement_difference"], "0.000")
        self.assertEqual(result["receipt_lot_remaining"], "8.000")
        self.assertEqual(result["unbatched_quantity"], "0.000")
        self.assertTrue(result["reconciled"])
        self.assertFalse(result["unbatched_warning"])

    def test_stock_reconciliation_flags_unbatched_opening_stock_without_false_mismatch(self):
        from inventory.services import reconcile_material_stock_balance

        self.balance.quantity = Decimal("12")
        self.balance.save(update_fields=["quantity", "updated_at"])
        MaterialStockMovement.objects.create(
            balance=self.balance, movement_type=MaterialStockMovement.Type.OPENING,
            quantity=Decimal("2"), balance_after=Decimal("2"), reference="OPENING-TEST",
        )
        MaterialStockMovement.objects.create(
            balance=self.balance, movement_type=MaterialStockMovement.Type.PURCHASE_RECEIPT,
            quantity=Decimal("10"), balance_after=Decimal("12"), reference="GRN-TEST",
        )

        result = reconcile_material_stock_balance(self.balance)

        self.assertEqual(result["movement_expected_balance"], "12.000")
        self.assertEqual(result["receipt_lot_remaining"], "10.000")
        self.assertEqual(result["unbatched_quantity"], "2.000")
        self.assertTrue(result["reconciled"])
        self.assertTrue(result["unbatched_warning"])

    def test_founder_can_cost_unbatched_opening_stock_with_verified_reference(self):
        from inventory.services import record_material_movement, issue_material
        admin = User.objects.create_superuser(
            username="opening-cost-admin", email="opening@example.com", password="StrongPass123!",
        )
        movement = record_material_movement(
            balance_id=self.balance.pk, movement_type=MaterialStockMovement.Type.OPENING,
            quantity="2", user=admin, reference="OPEN-COUNT-2026-11",
            remarks="Verified opening physical count.",
        )
        self.client.force_login(admin)
        response = self.client.get("/api/inventory/materials/opening-batches/unpriced/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row["movement_id"] for row in response.json()["items"]], [movement.pk])

        response = self.client.post(
            f"/api/inventory/materials/opening-batches/{movement.pk}/cost/",
            data=json.dumps({"unit_cost":"85.50","cost_source_reference":"Approved valuation sheet VAL-2026-11-16"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        lot = MaterialStockLot.objects.get(opening_movement=movement)
        self.assertEqual(lot.original_quantity, Decimal("2"))
        self.assertEqual(lot.remaining_quantity, Decimal("2"))
        self.assertEqual(lot.unit_cost, Decimal("85.50"))
        self.assertEqual(lot.cost_source_reference, "Approved valuation sheet VAL-2026-11-16")
        lot_response = self.client.get("/api/inventory/materials/lots/")
        self.assertEqual(lot_response.status_code, 200, lot_response.content)
        opening_row = next(row for row in lot_response.json()["items"] if row["id"] == lot.pk)
        self.assertEqual(opening_row["source_type"], "opening_stock")
        self.assertEqual(opening_row["opening_movement_id"], movement.pk)
        self.assertIsNone(opening_row["receipt_no"])

        issue, _ = issue_material(
            material_id=self.line.pk, quantity="1", lot_id=lot.pk, user=admin,
        )
        self.assertEqual(issue.unit_rate, Decimal("85.50"))
        lot.refresh_from_db()
        self.assertEqual(lot.remaining_quantity, Decimal("1"))

    def test_opening_stock_cannot_be_costed_without_source_reference(self):
        from inventory.services import record_material_movement
        admin = User.objects.create_superuser(
            username="opening-no-ref-admin", email="opening-no-ref@example.com", password="StrongPass123!",
        )
        movement = record_material_movement(
            balance_id=self.balance.pk, movement_type=MaterialStockMovement.Type.OPENING,
            quantity="2", user=admin, reference="OPEN-COUNT-2026-11",
        )
        self.client.force_login(admin)
        response = self.client.post(
            f"/api/inventory/materials/opening-batches/{movement.pk}/cost/",
            data=json.dumps({"unit_cost":"85.50","cost_source_reference":"  "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MaterialStockLot.objects.filter(opening_movement=movement).exists())

    def test_department_manager_cannot_assign_opening_stock_cost(self):
        from inventory.services import record_material_movement
        admin = User.objects.create_superuser(
            username="opening-permission-admin", email="opening-permission@example.com", password="StrongPass123!",
        )
        movement = record_material_movement(
            balance_id=self.balance.pk, movement_type=MaterialStockMovement.Type.OPENING,
            quantity="2", user=admin, reference="OPEN-COUNT-2026-11",
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            f"/api/inventory/materials/opening-batches/{movement.pk}/cost/",
            data=json.dumps({"unit_cost":"85.50","cost_source_reference":"Approved valuation sheet"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(MaterialStockLot.objects.filter(opening_movement=movement).exists())

    def test_stock_reconciliation_api_is_scoped_to_manager_department(self):
        MaterialStockBalance.objects.create(
            material=self.material, department=self.other_department,
            location="Other Store", quantity=Decimal("5"),
        )
        self.client.force_login(self.manager)
        response = self.client.get("/api/inventory/materials/reconciliation/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["items"][0]["balance_id"], self.balance.pk,
        )

    def test_issue_rejects_precision_not_supported_by_production_issue_records(self):
        with self.assertRaises(ValidationError):
            issue_material(material_id=self.line.pk, quantity="1.001", lot_id=self.lot.pk, user=self.manager)
        self.balance.refresh_from_db()
        self.lot.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("10"))
        self.assertEqual(self.lot.remaining_quantity, Decimal("10"))
        self.assertEqual(self.line.issued_quantity, Decimal("0"))
        self.assertFalse(self.line.inventory_issues.exists())

    def test_return_and_wastage_reject_precision_not_supported_by_issue_records(self):
        issue, _ = issue_material(
            material_id=self.line.pk, quantity="2", lot_id=self.lot.pk, user=self.manager,
        )
        with self.assertRaises(ValidationError):
            return_issued_material(material_issue_id=issue.pk, quantity="1.001", user=self.manager)
        with self.assertRaises(ValidationError):
            record_issued_wastage(material_issue_id=issue.pk, quantity="1.001", user=self.manager)
        issue.refresh_from_db()
        self.balance.refresh_from_db()
        self.lot.refresh_from_db()
        self.assertEqual(issue.returned_quantity, Decimal("0"))
        self.assertEqual(issue.wastage_quantity, Decimal("0"))
        self.assertEqual(self.balance.quantity, Decimal("8"))
        self.assertEqual(self.lot.remaining_quantity, Decimal("8"))

    def test_issue_rejects_insufficient_stock(self):
        with self.assertRaises(ValidationError):
            issue_material(material_id=self.line.pk, quantity="11", lot_id=self.lot.pk, user=self.manager)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("10"))

    def test_opening_stock_issue_appears_in_production_history_with_its_source(self):
        from inventory.services import record_material_movement

        admin = User.objects.create_superuser(
            username="opening-detail-admin", email="opening-detail@example.com", password="StrongPass123!",
        )
        movement = record_material_movement(
            balance_id=self.balance.pk, movement_type=MaterialStockMovement.Type.OPENING,
            quantity="2", user=admin, reference="OPENING-DETAIL",
        )
        self.client.force_login(admin)
        cost_response = self.client.post(
            f"/api/inventory/materials/opening-batches/{movement.pk}/cost/",
            data=json.dumps({
                "unit_cost": "85.50",
                "cost_source_reference": "Approved opening valuation OV-2026-01",
            }),
            content_type="application/json",
        )
        self.assertEqual(cost_response.status_code, 201, cost_response.content)
        opening_lot = MaterialStockLot.objects.get(opening_movement=movement)
        issue, _ = issue_material(
            material_id=self.line.pk, quantity="1", lot_id=opening_lot.pk, user=admin,
        )
        response = self.client.get(f"/api/production/jobs/{self.job.pk}/")
        self.assertEqual(response.status_code, 200, response.content)
        issue_row = next(row for row in response.json()["material_issues"] if row["id"] == issue.pk)
        self.assertEqual(issue_row["receipt_no"], f"Opening #{movement.pk}")
        self.assertEqual(issue_row["cost_source_reference"], "Approved opening valuation OV-2026-01")

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
        with self.assertRaises(ValidationError):
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

    def test_opening_stock_movement_rejects_invalid_quantity_precision(self):
        self.client.force_login(self.admin)
        for value in ("NaN", "Infinity", "1.0001", "100000000000"):
            with self.subTest(value=value):
                response = self.client.post(
                    "/api/inventory/materials/movements/create/",
                    data=json.dumps({"balance": self.balance.pk, "type": "opening", "quantity": value}),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("12"))
        self.assertFalse(MaterialStockMovement.objects.filter(balance=self.balance).exists())

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
        from inventory.services import reconcile_material_stock_balance
        reconciliation = reconcile_material_stock_balance(self.balance)
        self.assertEqual(reconciliation["movement_expected_balance"], "10.000")
        self.assertEqual(reconciliation["movement_difference"], "0.000")
        self.assertEqual(reconciliation["unknown_movement_types"], [])
        self.assertTrue(reconciliation["reconciled"])
        self.assertTrue(reconciliation["unbatched_warning"])

    def test_reject_does_not_change_stock(self):
        count = submit_material_stock_count(balance_id=self.balance.pk, counted_quantity="15", user=self.manager)
        reviewed = review_material_stock_count(count_id=count.pk, approve=False, user=self.admin)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("12"))
        self.assertEqual(reviewed.status, MaterialStockCount.Status.REJECTED)

    def test_count_submission_rejects_non_finite_quantity(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                submit_material_stock_count(
                    balance_id=self.balance.pk, counted_quantity=value, user=self.manager
                )

    def test_count_submission_rejects_more_than_three_decimal_places(self):
        with self.assertRaisesMessage(ValidationError, "three decimal places"):
            submit_material_stock_count(
                balance_id=self.balance.pk, counted_quantity="10.0001", user=self.manager
            )
        self.assertFalse(MaterialStockCount.objects.exists())

    def test_count_submission_rejects_quantity_above_decimal_field_capacity(self):
        with self.assertRaisesMessage(ValidationError, "supported stock quantity"):
            submit_material_stock_count(
                balance_id=self.balance.pk, counted_quantity="100000000000", user=self.manager
            )
        self.assertFalse(MaterialStockCount.objects.exists())

    def test_manager_cannot_submit_stock_count_for_another_department(self):
        other_department = Department.objects.create(code="count-b", name="Count B")
        foreign_balance = MaterialStockBalance.objects.create(
            material=self.balance.material, department=other_department,
            location="Foreign Store", quantity=Decimal("7"),
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/inventory/materials/stock-counts/submit/",
            data=json.dumps({"balance": foreign_balance.pk, "counted_quantity": "6"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(MaterialStockCount.objects.filter(balance=foreign_balance).exists())

    def test_department_manager_cannot_review_stock_count_variance(self):
        count = submit_material_stock_count(
            balance_id=self.balance.pk, counted_quantity="10", user=self.manager
        )
        self.client.force_login(self.manager)
        response = self.client.post(
            f"/api/inventory/materials/stock-counts/{count.pk}/review/",
            data=json.dumps({"approve": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.balance.refresh_from_db()
        count.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("12"))
        self.assertEqual(count.status, MaterialStockCount.Status.PENDING)

    def test_stale_count_cannot_be_approved(self):
        count = submit_material_stock_count(balance_id=self.balance.pk, counted_quantity="10", user=self.manager)
        self.balance.quantity = Decimal("11")
        self.balance.save(update_fields=["quantity", "updated_at"])
        with self.assertRaisesMessage(ValidationError, "Stock changed after this count"):
            review_material_stock_count(count_id=count.pk, approve=True, user=self.admin)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("11"))


class ReusableOffcutAreaLedgerTests(TestCase):
    def setUp(self):
        from inventory.models import ReusableOffcut, OffcutUsage
        from inventory.services import issue_material
        from purchase.models import Supplier, PurchaseOrder, PurchaseItem, GoodsReceipt, GoodsReceiptLine, MaterialStockLot

        self.department = Department.objects.create(code="offcut-a", name="Offcut A")
        self.manager = User.objects.create_user(username="offcut-manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        customer = Customer.objects.create(name="Offcut Customer", phone="9000000011", department=self.department)
        self.source_job = ProductionJob.objects.create(
            order=SalesOrder.objects.create(customer=customer, item_description="Source job", quantity=1, confirmed_price=Decimal("1000")),
            station=ProductionJob.Station.LASER,
        )
        self.target_job = ProductionJob.objects.create(
            order=SalesOrder.objects.create(customer=customer, item_description="Target job", quantity=1, confirmed_price=Decimal("1000")),
            station=ProductionJob.Station.LASER,
        )
        self.material = MaterialVariant.objects.create(
            material_name="Offcut Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("100"), unit="Sheet", sheet_width_ft=Decimal("8"), sheet_height_ft=Decimal("4"),
        )
        self.source_line = ProductionMaterial.objects.create(
            job=self.source_job, material_variant=self.material, material_name="Offcut Acrylic",
            quantity_required=Decimal("2"), unit="Sheet",
        )
        self.target_line = ProductionMaterial.objects.create(
            job=self.target_job, material_variant=self.material, material_name="Offcut Acrylic",
            quantity_required=Decimal("2"), unit="Sheet",
        )
        supplier = Supplier.objects.create(name="Offcut Supplier")
        po = PurchaseOrder.objects.create(
            supplier=supplier, department=self.department, status=PurchaseOrder.Status.SENT,
        )
        item = PurchaseItem.objects.create(
            purchase_order=po, material_variant=self.material,
            quantity=Decimal("10"), unit_cost=Decimal("100"),
        )
        # Exercise the real Goods Receipt API so this workflow verifies
        # Purchase → department stock balance → receipt lot → production issue.
        from django.test import RequestFactory
        from purchase.api import receive
        request = RequestFactory().post(
            f"/api/purchase/orders/{po.pk}/receive/",
            data=json.dumps({
                "received_date": "2026-11-16", "location": "Offcut Store",
                "items": [{"purchase_item_id": item.pk, "received_quantity": "10"}],
            }),
            content_type="application/json",
        )
        request.user = self.manager
        receipt_response = receive(request, po.pk)
        self.assertEqual(receipt_response.status_code, 200, receipt_response.content.decode())
        receipt_line = GoodsReceiptLine.objects.get(receipt__purchase_order=po, purchase_item=item)
        self.lot = receipt_line.stock_lot
        self.balance = self.lot.balance
        self.assertEqual(self.balance.quantity, Decimal("10"))
        self.assertEqual(self.lot.unit_cost, Decimal("100"))
        self.issue, _ = issue_material(
            material_id=self.source_line.pk, quantity="1", lot_id=self.lot.pk, user=self.manager,
        )
        self.client.force_login(self.manager)

    def _create_offcut(self, usable_area="10"):
        return self.client.post(
            "/api/inventory/materials/offcuts/create/",
            data=json.dumps({
                "material": self.material.pk, "location": "Offcut Rack",
                "length_mm": "1000", "width_mm": "1000", "usable_area_sqft": usable_area,
                "source_issue": self.issue.pk,
            }),
            content_type="application/json",
        )

    def test_offcut_registration_snapshots_source_batch_cost_per_square_foot(self):
        response = self._create_offcut()
        self.assertEqual(response.status_code, 201, response.content)
        from inventory.models import ReusableOffcut
        offcut = ReusableOffcut.objects.get(pk=response.json()["id"])
        self.assertEqual(offcut.source_issue_id, self.issue.pk)
        self.assertEqual(offcut.source_lot_id, self.issue.stock_lot_id)
        self.assertEqual(offcut.cost_per_sqft, Decimal("3.125000"))

    def test_offcut_thickness_must_match_source_material_master(self):
        from inventory.models import ReusableOffcut
        response = self.client.post(
            "/api/inventory/materials/offcuts/create/",
            data=json.dumps({
                "material": self.material.pk, "location": "Offcut Rack",
                "length_mm": "1000", "width_mm": "1000",
                "usable_area_sqft": "10", "source_issue": self.issue.pk,
                "thickness_mm": "5",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("match the source Material Master thickness", response.json()["detail"])
        self.assertFalse(ReusableOffcut.objects.exists())

    def test_offcut_dimensions_cannot_exceed_one_source_sheet(self):
        response = self.client.post(
            "/api/inventory/materials/offcuts/create/",
            data=json.dumps({
                "material": self.material.pk, "location": "Offcut Rack",
                "length_mm": "3000", "width_mm": "100",
                "usable_area_sqft": "1", "source_issue": self.issue.pk,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot exceed one source sheet", response.json()["detail"])

    def test_offcut_rejects_non_finite_and_over_precision_measurements(self):
        from inventory.models import ReusableOffcut
        invalid_payloads = [
            {"length_mm": "NaN", "width_mm": "100", "usable_area_sqft": "1"},
            {"length_mm": "100.001", "width_mm": "100", "usable_area_sqft": "1"},
            {"length_mm": "100", "width_mm": "100", "usable_area_sqft": "1.00001"},
            {"length_mm": "100000000.00", "width_mm": "100", "usable_area_sqft": "1"},
        ]
        for values in invalid_payloads:
            with self.subTest(values=values):
                response = self.client.post(
                    "/api/inventory/materials/offcuts/create/",
                    data=json.dumps({
                        "material": self.material.pk, "location": "Offcut Rack",
                        "source_issue": self.issue.pk, **values,
                    }),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(ReusableOffcut.objects.exists())

    def test_offcut_area_cannot_exceed_measured_rectangle(self):
        from inventory.models import ReusableOffcut
        response = self._create_offcut(usable_area="11")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ReusableOffcut.objects.exists())

    def test_offcut_usage_can_be_partial_and_is_costed_to_matching_job_material(self):
        response = self._create_offcut()
        self.assertEqual(response.status_code, 201, response.content)
        offcut_id = response.json()["id"]
        first = self.client.post(
            f"/api/inventory/materials/offcuts/{offcut_id}/action/",
            data=json.dumps({"action": "used", "job": self.target_job.pk, "material_line": self.target_line.pk, "used_area_sqft": "4"}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(first.json()["remaining_area_sqft"], "6.0000")
        self.assertEqual(first.json()["allocated_cost"], "12.50")
        from inventory.models import ReusableOffcut, OffcutUsage
        offcut = ReusableOffcut.objects.get(pk=offcut_id)
        self.assertEqual(offcut.status, ReusableOffcut.Status.AVAILABLE)
        second = self.client.post(
            f"/api/inventory/materials/offcuts/{offcut_id}/action/",
            data=json.dumps({"action": "used", "job": self.target_job.pk, "material_line": self.target_line.pk, "used_area_sqft": "6"}),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200, second.content)
        offcut.refresh_from_db()
        self.assertEqual(offcut.status, ReusableOffcut.Status.USED)
        self.assertEqual(OffcutUsage.objects.filter(offcut=offcut).count(), 2)
        self.assertEqual(sum(OffcutUsage.objects.filter(offcut=offcut).values_list("total_cost", flat=True)), Decimal("31.25"))

    def test_job_cost_summary_transfers_offcut_value_and_records_discard_writeoff(self):
        from inventory.models import ReusableOffcut
        from production.api import _job_material_cost_summary

        response = self._create_offcut(usable_area="10")
        self.assertEqual(response.status_code, 201, response.content)
        offcut = ReusableOffcut.objects.get(pk=response.json()["id"])

        source_summary = _job_material_cost_summary(self.source_job)
        self.assertEqual(source_summary["issued_material_cost"], "100.00")
        self.assertEqual(source_summary["offcut_salvage_credit"], "31.25")
        self.assertEqual(source_summary["net_material_cost"], "68.75")
        self.assertEqual(source_summary["offcut_inventory_value"], "31.25")

        use_response = self.client.post(
            f"/api/inventory/materials/offcuts/{offcut.pk}/action/",
            data=json.dumps({"action": "used", "job": self.target_job.pk, "material_line": self.target_line.pk, "used_area_sqft": "4"}),
            content_type="application/json",
        )
        self.assertEqual(use_response.status_code, 200, use_response.content)
        target_summary = _job_material_cost_summary(self.target_job)
        self.assertEqual(target_summary["offcut_consumed_cost"], "12.50")
        self.assertEqual(target_summary["net_material_cost"], "12.50")
        self.assertEqual(_job_material_cost_summary(self.source_job)["offcut_inventory_value"], "18.75")

        discard_response = self.client.post(
            f"/api/inventory/materials/offcuts/{offcut.pk}/action/",
            data=json.dumps({"action": "discarded"}),
            content_type="application/json",
        )
        self.assertEqual(discard_response.status_code, 200, discard_response.content)
        offcut.refresh_from_db()
        self.assertEqual(offcut.discarded_area_sqft, Decimal("6"))
        self.assertEqual(offcut.discarded_cost, Decimal("18.75"))
        source_summary = _job_material_cost_summary(self.source_job)
        self.assertEqual(source_summary["offcut_discard_writeoff"], "18.75")
        self.assertEqual(source_summary["offcut_inventory_value"], "0.00")
        self.assertEqual(source_summary["net_material_cost"], "87.50")

    def test_return_cannot_restore_sheet_area_already_registered_as_offcut(self):
        response = self._create_offcut(usable_area="10")
        self.assertEqual(response.status_code, 201, response.content)
        with self.assertRaisesMessage(ValidationError, "after registered offcuts"):
            return_issued_material(material_issue_id=self.issue.pk, quantity="0.70", user=self.manager)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("9"))
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.returned_quantity, Decimal("0"))

    def test_wastage_cannot_double_count_sheet_area_registered_as_offcut(self):
        response = self._create_offcut(usable_area="10")
        self.assertEqual(response.status_code, 201, response.content)
        with self.assertRaisesMessage(ValidationError, "after registered offcuts"):
            record_issued_wastage(material_issue_id=self.issue.pk, quantity="0.70", user=self.manager)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.wastage_quantity, Decimal("0"))

    def test_offcut_cannot_be_used_for_another_material_or_department(self):
        response = self._create_offcut()
        self.assertEqual(response.status_code, 201, response.content)
        other_material = MaterialVariant.objects.create(material_name="Other Sheet", unit="Sheet")
        wrong_line = ProductionMaterial.objects.create(
            job=self.target_job, material_variant=other_material, material_name="Other Sheet",
            quantity_required=Decimal("1"), unit="Sheet",
        )
        rejected = self.client.post(
            f"/api/inventory/materials/offcuts/{response.json()['id']}/action/",
            data=json.dumps({"action": "used", "job": self.target_job.pk, "material_line": wrong_line.pk, "used_area_sqft": "1"}),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)
        from inventory.models import OffcutUsage
        self.assertFalse(OffcutUsage.objects.exists())


    def test_offcut_usage_cannot_exceed_remaining_sheet_requirement_area(self):
        from inventory.models import OffcutUsage
        from production.models import ProductionMaterial

        small_line = ProductionMaterial.objects.create(
            job=self.target_job, material_variant=self.material, material_name="Offcut Acrylic",
            quantity_required=Decimal("0.10"), unit="Sheet",
        )
        response = self._create_offcut(usable_area="10")
        self.assertEqual(response.status_code, 201, response.content)
        rejected = self.client.post(
            f"/api/inventory/materials/offcuts/{response.json()['id']}/action/",
            data=json.dumps({
                "action": "used", "job": self.target_job.pk,
                "material_line": small_line.pk, "used_area_sqft": "4",
            }),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("no more than 3.2000 additional sq ft", rejected.json()["detail"])
        self.assertFalse(OffcutUsage.objects.filter(target_material=small_line).exists())

    def test_offcut_area_reduces_sheet_issue_requirement_and_prevents_overissue(self):
        from inventory.services import issue_material

        response = self._create_offcut(usable_area="10")
        self.assertEqual(response.status_code, 201, response.content)
        used = self.client.post(
            f"/api/inventory/materials/offcuts/{response.json()['id']}/action/",
            data=json.dumps({
                "action": "used", "job": self.target_job.pk,
                "material_line": self.target_line.pk, "used_area_sqft": "4",
            }),
            content_type="application/json",
        )
        self.assertEqual(used.status_code, 200, used.content)
        self.target_line.refresh_from_db()
        self.assertEqual(self.target_line.offcut_equivalent_quantity, Decimal("0.125"))
        self.assertEqual(self.target_line.pending_quantity, Decimal("1.875"))

        with self.assertRaisesMessage(ValidationError, "Cannot issue more than pending requirement"):
            issue_material(
                material_id=self.target_line.pk, quantity="1.88",
                lot_id=self.lot.pk, user=self.manager,
            )
        issue_material(
            material_id=self.target_line.pk, quantity="1.87",
            lot_id=self.lot.pk, user=self.manager,
        )
        self.target_line.refresh_from_db()
        self.assertEqual(self.target_line.issued_quantity, Decimal("1.87"))
        self.assertEqual(self.target_line.pending_quantity, Decimal("0"))


    def test_end_to_end_receipt_issue_return_wastage_and_offcut_cost_transfer(self):
        from inventory.models import ReusableOffcut
        from inventory.services import reconcile_material_stock_balance, return_issued_material, record_issued_wastage
        from production.api import _job_material_cost_summary

        # Receive 10 sheets at ₹100/sheet, then issue one sheet to the source job.
        response = self._create_offcut(usable_area="8")
        self.assertEqual(response.status_code, 201, response.content)
        offcut = ReusableOffcut.objects.get(pk=response.json()["id"])

        # The 8 sq ft offcut is 0.25 sheet (32 sq ft per source sheet).
        # Return 0.50 sheet and attribute the remaining 0.25 sheet as wastage.
        return_issued_material(
            material_issue_id=self.issue.pk, quantity="0.50", user=self.manager,
        )
        record_issued_wastage(
            material_issue_id=self.issue.pk, quantity="0.25", user=self.manager,
        )

        self.issue.refresh_from_db()
        self.balance.refresh_from_db()
        self.lot.refresh_from_db()
        self.assertEqual(self.issue.returned_quantity, Decimal("0.50"))
        self.assertEqual(self.issue.wastage_quantity, Decimal("0.25"))
        self.assertEqual(self.balance.quantity, Decimal("9.50"))
        self.assertEqual(self.lot.remaining_quantity, Decimal("9.50"))

        reconciliation = reconcile_material_stock_balance(self.balance)
        self.assertEqual(reconciliation["movement_expected_balance"], "9.500")
        self.assertEqual(reconciliation["receipt_lot_remaining"], "9.500")
        self.assertEqual(reconciliation["movement_difference"], "0.000")
        self.assertTrue(reconciliation["reconciled"])

        source_before_transfer = _job_material_cost_summary(self.source_job)
        self.assertEqual(source_before_transfer["issued_material_cost"], "100.00")
        self.assertEqual(source_before_transfer["returned_material_credit"], "50.00")
        self.assertEqual(source_before_transfer["offcut_salvage_credit"], "25.00")
        self.assertEqual(source_before_transfer["net_material_cost"], "25.00")
        self.assertEqual(source_before_transfer["offcut_inventory_value"], "25.00")

        # Consume half of the offcut in the target job, then write off the remainder.
        use_response = self.client.post(
            f"/api/inventory/materials/offcuts/{offcut.pk}/action/",
            data=json.dumps({
                "action": "used", "job": self.target_job.pk,
                "material_line": self.target_line.pk, "used_area_sqft": "4",
            }),
            content_type="application/json",
        )
        self.assertEqual(use_response.status_code, 200, use_response.content)
        self.assertEqual(use_response.json()["allocated_cost"], "12.50")

        target_summary = _job_material_cost_summary(self.target_job)
        self.assertEqual(target_summary["offcut_consumed_cost"], "12.50")
        self.assertEqual(target_summary["net_material_cost"], "12.50")
        self.assertEqual(_job_material_cost_summary(self.source_job)["offcut_inventory_value"], "12.50")

        discard_response = self.client.post(
            f"/api/inventory/materials/offcuts/{offcut.pk}/action/",
            data=json.dumps({"action": "discarded"}),
            content_type="application/json",
        )
        self.assertEqual(discard_response.status_code, 200, discard_response.content)
        offcut.refresh_from_db()
        self.assertEqual(offcut.discarded_area_sqft, Decimal("4"))
        self.assertEqual(offcut.discarded_cost, Decimal("12.50"))

        source_final = _job_material_cost_summary(self.source_job)
        target_final = _job_material_cost_summary(self.target_job)
        self.assertEqual(source_final["offcut_discard_writeoff"], "12.50")
        self.assertEqual(source_final["offcut_inventory_value"], "0.00")
        self.assertEqual(source_final["net_material_cost"], "37.50")
        self.assertEqual(target_final["net_material_cost"], "12.50")
        # ₹50 return credit + ₹37.50 source cost + ₹12.50 target cost = ₹100 issued value.
        self.assertEqual(
            Decimal(source_final["net_material_cost"]) + Decimal(target_final["net_material_cost"]),
            Decimal("50.00"),
        )


class MaterialIssueEmployeeDepartmentAPITests(TestCase):
    def setUp(self):
        from staff.models import StaffProfile

        self.department = Department.objects.create(code="issue-employee-a", name="Issue Employee A")
        self.other_department = Department.objects.create(code="issue-employee-b", name="Issue Employee B")
        self.manager = User.objects.create_user(username="issue_employee_manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager, role=UserProfile.Role.MANAGER, department=self.department
        )
        customer = Customer.objects.create(
            name="Issue Employee Customer", phone="9000000033", department=self.department
        )
        order = SalesOrder.objects.create(
            customer=customer, item_description="Issue Employee Job",
            quantity=1, confirmed_price=1000,
        )
        self.job = ProductionJob.objects.create(order=order, station=ProductionJob.Station.LASER)
        material = MaterialVariant.objects.create(
            material_name="Issue Employee Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("100"), unit="Sheet",
        )
        self.balance = MaterialStockBalance.objects.create(
            material=material, department=self.department, location="Main Store",
            quantity=Decimal("10"),
        )
        self.line = ProductionMaterial.objects.create(
            job=self.job, material_variant=material, material_name="Issue Employee Acrylic",
            quantity_required=Decimal("5"), unit="Sheet",
        )
        from staff.models import StaffProfile
        foreign_user = User.objects.create_user(username="foreign_issue_employee", password="StrongPass123!")
        UserProfile.objects.create(
            user=foreign_user, role=UserProfile.Role.STAFF, department=self.other_department
        )
        self.foreign_employee = StaffProfile.objects.create(
            user=foreign_user, staff_id="FOREIGN-ISSUE-01", department=self.other_department
        )
        self.client.force_login(self.manager)

    def test_inactive_employee_cannot_be_attributed_to_material_return(self):
        from staff.models import StaffProfile
        staff_user = User.objects.create_user(username="inactive_return_staff", password="StrongPass123!")
        UserProfile.objects.create(user=staff_user, role=UserProfile.Role.STAFF, department=self.department)
        employee = StaffProfile.objects.create(
            user=staff_user, staff_id="INACTIVE-RETURN-01", department=self.department,
            status=StaffProfile.Status.INACTIVE,
        )
        response = self.client.post(
            "/api/inventory/materials/returns/create/",
            data=json.dumps({"material_line": self.source_line.pk, "material_issue": self.issue.pk,
                             "quantity": "0.10", "employee": employee.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("active employee", response.json()["detail"])
        self.issue.refresh_from_db()
        self.balance.refresh_from_db()
        self.assertEqual(self.issue.returned_quantity, Decimal("0"))
        self.assertEqual(self.balance.quantity, Decimal("9"))

    def test_inactive_employee_cannot_be_attributed_to_material_wastage(self):
        from staff.models import StaffProfile
        staff_user = User.objects.create_user(username="inactive_wastage_staff", password="StrongPass123!")
        UserProfile.objects.create(user=staff_user, role=UserProfile.Role.STAFF, department=self.department)
        employee = StaffProfile.objects.create(
            user=staff_user, staff_id="INACTIVE-WASTE-01", department=self.department,
            status=StaffProfile.Status.INACTIVE,
        )
        response = self.client.post(
            "/api/inventory/materials/wastage/create/",
            data=json.dumps({"material_line": self.source_line.pk, "material_issue": self.issue.pk,
                             "quantity": "0.10", "employee": employee.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("active employee", response.json()["detail"])
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.wastage_quantity, Decimal("0"))

    def test_manager_cannot_record_material_issue_against_foreign_department_employee(self):
        response = self.client.post(
            "/api/inventory/materials/issues/create/",
            data=json.dumps({
                "material_line": self.line.pk,
                "quantity": "1",
                "balance": self.balance.pk,
                "employee": self.foreign_employee.pk,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("production job department", response.json()["detail"])
        self.balance.refresh_from_db()
        self.line.refresh_from_db()
        self.assertEqual(self.balance.quantity, Decimal("10"))
        self.assertEqual(self.line.issued_quantity, Decimal("0"))



class StockReconciliationPaginationApiTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="recon-page-a", name="Reconciliation Page A")
        self.other_department = Department.objects.create(code="recon-page-b", name="Reconciliation Page B")
        self.admin = User.objects.create_superuser(
            username="recon-page-admin", email="recon-page@example.com", password="StrongPass123!",
        )
        self.manager = User.objects.create_user(
            username="recon-page-manager", password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.manager, role=UserProfile.Role.MANAGER, department=self.department,
        )
        self.material = MaterialVariant.objects.create(
            material_name="Reconciliation Page Material", unit="Sheet",
        )

    def _create_balances(self, department, count, prefix):
        return MaterialStockBalance.objects.bulk_create([
            MaterialStockBalance(
                material=self.material, department=department,
                location=f"{prefix}-{index:03d}", quantity=Decimal("0"),
            )
            for index in range(count)
        ])

    def test_reconciliation_pages_cover_every_balance_without_duplicates(self):
        self._create_balances(self.department, 205, "Admin Store")
        self.client.force_login(self.admin)

        first = self.client.get("/api/inventory/materials/reconciliation/?page=1")
        second = self.client.get("/api/inventory/materials/reconciliation/?page=2")
        third = self.client.get("/api/inventory/materials/reconciliation/?page=3")

        for response in (first, second, third):
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["total_count"], 205)
            self.assertEqual(response.json()["page_size"], 100)
            self.assertFalse(response.json()["truncated"])

        first_data, second_data, third_data = (r.json() for r in (first, second, third))
        self.assertEqual([first_data["count"], second_data["count"], third_data["count"]], [100, 100, 5])
        self.assertTrue(first_data["has_next"])
        self.assertTrue(second_data["has_previous"])
        self.assertTrue(second_data["has_next"])
        self.assertTrue(third_data["has_previous"])
        self.assertFalse(third_data["has_next"])

        ids = (
            [row["balance_id"] for row in first_data["items"]]
            + [row["balance_id"] for row in second_data["items"]]
            + [row["balance_id"] for row in third_data["items"]]
        )
        self.assertEqual(len(ids), 205)
        self.assertEqual(len(set(ids)), 205)

    def test_reconciliation_pagination_respects_manager_department_scope(self):
        self._create_balances(self.department, 101, "Manager Store")
        self._create_balances(self.other_department, 3, "Other Store")
        self.client.force_login(self.manager)

        first = self.client.get("/api/inventory/materials/reconciliation/?page=1")
        second = self.client.get("/api/inventory/materials/reconciliation/?page=2")

        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json()["total_count"], 101)
        self.assertEqual(first.json()["count"], 100)
        self.assertEqual(second.json()["count"], 1)
        self.assertEqual(
            {row["department_id"] for response in (first, second) for row in response.json()["items"]},
            {self.department.pk},
        )

    def test_reconciliation_rejects_invalid_page_numbers(self):
        self._create_balances(self.department, 1, "Invalid Page Store")
        self.client.force_login(self.admin)

        for page in ("0", "-1", "not-a-number"):
            with self.subTest(page=page):
                response = self.client.get(f"/api/inventory/materials/reconciliation/?page={page}")
                self.assertEqual(response.status_code, 400)
                self.assertIn("positive integer", response.json()["detail"])

    def test_uncosted_opening_stock_paginates_without_omitting_records(self):
        balances = self._create_balances(self.department, 205, "Opening Page Store")
        MaterialStockMovement.objects.bulk_create([
            MaterialStockMovement(
                balance=balance, movement_type=MaterialStockMovement.Type.OPENING,
                quantity=Decimal("1"), balance_after=Decimal("1"),
                reference=f"OPEN-{index:03d}",
            )
            for index, balance in enumerate(balances)
        ])
        self.client.force_login(self.admin)

        first = self.client.get("/api/inventory/materials/opening-batches/unpriced/?page=1")
        second = self.client.get("/api/inventory/materials/opening-batches/unpriced/?page=2")
        third = self.client.get("/api/inventory/materials/opening-batches/unpriced/?page=3")
        for response in (first, second, third):
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["total_count"], 205)
            self.assertEqual(response.json()["page_size"], 100)

        payloads = [response.json() for response in (first, second, third)]
        self.assertEqual([payload["count"] for payload in payloads], [100, 100, 5])
        ids = [row["movement_id"] for payload in payloads for row in payload["items"]]
        self.assertEqual(len(ids), 205)
        self.assertEqual(len(set(ids)), 205)
        self.assertFalse(payloads[0]["has_previous"])
        self.assertTrue(payloads[1]["has_previous"])
        self.assertTrue(payloads[1]["has_next"])
        self.assertFalse(payloads[2]["has_next"])

    def test_reconciliation_summary_is_global_not_page_scoped(self):
        balances = self._create_balances(self.department, 205, "Global Summary Store")
        # One deliberately inconsistent balance is placed on page one.
        balances[0].quantity = Decimal("3")
        balances[0].save(update_fields=["quantity"])
        self.client.force_login(self.admin)

        first = self.client.get("/api/inventory/materials/reconciliation/?page=1")
        second = self.client.get("/api/inventory/materials/reconciliation/?page=2")
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)

        for payload in (first.json(), second.json()):
            self.assertEqual(payload["summary_scope"], "all_visible_balances")
            self.assertEqual(payload["reconciled_count"], 204)
            self.assertEqual(payload["mismatch_count"], 1)
            self.assertEqual(payload["unbatched_count"], 1)

        # Page two contains only reconciled rows, but still reports the same
        # global summary as page one.
        self.assertTrue(all(row["reconciled"] for row in second.json()["items"]))
