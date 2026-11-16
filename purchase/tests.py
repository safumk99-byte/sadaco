from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied

from accounts.models import UserProfile
from core.models import Department
from .models import PurchaseOrder, Supplier, PurchaseItem, GoodsReceiptLine
from .api import _purchase_orders, summary


class PurchaseDepartmentAccessTests(TestCase):
    def setUp(self):
        self.a = Department.objects.create(code="purchase-a", name="Purchase A")
        self.b = Department.objects.create(code="purchase-b", name="Purchase B")
        self.manager = User.objects.create_user(username="purchase_a_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.a)
        self.other = User.objects.create_user(username="purchase_b_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other, role=UserProfile.Role.MANAGER, department=self.b)
        supplier = Supplier.objects.create(name="Common Supplier")
        self.own = PurchaseOrder.objects.create(supplier=supplier, created_by=self.manager)
        self.foreign = PurchaseOrder.objects.create(supplier=supplier, created_by=self.other)

    def test_manager_sees_only_own_department_purchase_orders(self):
        self.assertEqual(set(_purchase_orders(self.manager).values_list("id", flat=True)), {self.own.id})

    def test_global_admin_sees_all_purchase_orders(self):
        admin = User.objects.create_superuser(username="purchase_root", password="StrongPass123!")
        self.assertEqual(_purchase_orders(admin).count(), 2)

    def test_unassigned_manager_sees_no_purchase_orders(self):
        user = User.objects.create_user(username="purchase_unassigned", password="StrongPass123!")
        UserProfile.objects.create(user=user, role=UserProfile.Role.MANAGER)
        self.assertFalse(_purchase_orders(user).exists())

    def test_non_manager_cannot_access_purchase_summary(self):
        staff = User.objects.create_user(username="purchase_staff", password="StrongPass123!")
        UserProfile.objects.create(user=staff, role=UserProfile.Role.STAFF, department=self.a)
        request = RequestFactory().get("/api/purchase/summary/")
        request.user = staff
        with self.assertRaises(PermissionDenied):
            summary(request)

    def test_material_goods_receipt_creates_auditable_stock_line_once(self):
        import json
        from decimal import Decimal
        from django.test import RequestFactory
        from products.models import MaterialVariant
        from inventory.models import MaterialStockBalance
        from .api import receive

        self.own.department = self.a
        self.own.status = PurchaseOrder.Status.SENT
        self.own.save(update_fields=["department", "status", "updated_at"])
        material = MaterialVariant.objects.create(
            material_name="Receipt Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("80"), unit="Sheet",
        )
        item = PurchaseItem.objects.create(
            purchase_order=self.own, material_variant=material,
            quantity=Decimal("4"), unit_cost=Decimal("125"),
        )
        request = RequestFactory().post(
            f"/api/purchase/orders/{self.own.pk}/receive/",
            data=json.dumps({"received_date": "2026-11-15", "location": "Main Store", "supplier_reference": "INV-001"}),
            content_type="application/json",
        )
        request.user = self.manager
        response = receive(request, self.own.pk)
        self.assertEqual(response.status_code, 200, response.content.decode())
        line = GoodsReceiptLine.objects.get(receipt__purchase_order=self.own, purchase_item=item)
        self.assertEqual(line.received_quantity, Decimal("4"))
        self.assertEqual(line.unit_cost, Decimal("125"))
        self.assertIsNotNone(line.material_stock_movement_id)
        balance = MaterialStockBalance.objects.get(material=material, department=self.a, location="Main Store")
        self.assertEqual(balance.quantity, Decimal("4"))
        lot = line.stock_lot
        self.assertEqual(lot.original_quantity, Decimal("4"))
        self.assertEqual(lot.remaining_quantity, Decimal("4"))
        self.assertEqual(lot.unit_cost, Decimal("125"))
        self.assertEqual(lot.balance_id, balance.pk)

        second = RequestFactory().post(
            f"/api/purchase/orders/{self.own.pk}/receive/",
            data=json.dumps({"location": "Main Store"}),
            content_type="application/json",
        )
        second.user = self.manager
        repeated = receive(second, self.own.pk)
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(GoodsReceiptLine.objects.filter(purchase_item=item).count(), 1)
        balance.refresh_from_db()
        self.assertEqual(balance.quantity, Decimal("4"))

    def test_partial_goods_receipts_can_be_recorded_in_multiple_batches(self):
        import json
        from decimal import Decimal
        from django.test import RequestFactory
        from products.models import MaterialVariant
        from inventory.models import MaterialStockBalance, MaterialStockMovement
        from .api import receive

        self.own.department = self.a
        self.own.status = PurchaseOrder.Status.SENT
        self.own.save(update_fields=["department", "status", "updated_at"])
        material = MaterialVariant.objects.create(
            material_name="Partial Receipt Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("80"), unit="Sheet",
        )
        item = PurchaseItem.objects.create(
            purchase_order=self.own, material_variant=material,
            quantity=Decimal("4"), unit_cost=Decimal("125"),
        )

        def post_receipt(quantity, reference):
            request = RequestFactory().post(
                f"/api/purchase/orders/{self.own.pk}/receive/",
                data=json.dumps({
                    "received_date": "2026-11-16",
                    "location": "Main Store",
                    "supplier_reference": reference,
                    "items": [{"purchase_item_id": item.pk, "received_quantity": str(quantity)}],
                }),
                content_type="application/json",
            )
            request.user = self.manager
            return receive(request, self.own.pk)

        first = post_receipt("1.5", "INV-PART-1")
        self.assertEqual(first.status_code, 200, first.content.decode())
        self.own.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(self.own.status, PurchaseOrder.Status.PARTIAL)
        self.assertEqual(item.received_quantity, Decimal("1.5"))
        self.assertEqual(item.pending_quantity, Decimal("2.5"))

        second = post_receipt("1.0", "INV-PART-2")
        self.assertEqual(second.status_code, 200, second.content.decode())
        self.own.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(self.own.status, PurchaseOrder.Status.PARTIAL)
        self.assertEqual(item.received_quantity, Decimal("2.5"))
        self.assertEqual(item.pending_quantity, Decimal("1.5"))

        lines = GoodsReceiptLine.objects.filter(purchase_item=item).order_by("id")
        self.assertEqual(lines.count(), 2)
        self.assertEqual(
            list(lines.values_list("received_quantity", flat=True)),
            [Decimal("1.5"), Decimal("1.0")],
        )
        self.assertEqual(
            list(lines.values_list("unit_cost", flat=True)),
            [Decimal("125"), Decimal("125")],
        )
        self.assertEqual(
            lines.filter(material_stock_movement__movement_type=MaterialStockMovement.Type.PURCHASE_RECEIPT).count(),
            2,
        )
        balance = MaterialStockBalance.objects.get(material=material, department=self.a, location="Main Store")
        self.assertEqual(balance.quantity, Decimal("2.5"))
        self.assertEqual(sum((line.stock_lot.original_quantity for line in lines), Decimal("0")), Decimal("2.5"))
        self.assertEqual(sum((line.stock_lot.remaining_quantity for line in lines), Decimal("0")), Decimal("2.5"))

    def test_receipt_rejects_quantity_above_pending_without_writing_stock(self):
        import json
        from decimal import Decimal
        from django.test import RequestFactory
        from products.models import MaterialVariant
        from inventory.models import MaterialStockBalance
        from .api import receive

        self.own.department = self.a
        self.own.status = PurchaseOrder.Status.SENT
        self.own.save(update_fields=["department", "status", "updated_at"])
        material = MaterialVariant.objects.create(
            material_name="Over Receipt Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("80"), unit="Sheet",
        )
        item = PurchaseItem.objects.create(
            purchase_order=self.own, material_variant=material,
            quantity=Decimal("4"), unit_cost=Decimal("125"),
        )
        request = RequestFactory().post(
            f"/api/purchase/orders/{self.own.pk}/receive/",
            data=json.dumps({
                "location": "Main Store",
                "items": [{"purchase_item_id": item.pk, "received_quantity": "4.01"}],
            }),
            content_type="application/json",
        )
        request.user = self.manager
        response = receive(request, self.own.pk)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.own.receipts.exists())
        self.assertFalse(MaterialStockBalance.objects.exists())
        item.refresh_from_db()
        self.assertEqual(item.received_quantity, Decimal("0"))

    def test_cancelled_purchase_order_cannot_receive_goods(self):
        from django.test import RequestFactory
        from django.core.exceptions import PermissionDenied
        from .api import receive
        self.own.status = PurchaseOrder.Status.CANCELLED
        self.own.save(update_fields=["status", "updated_at"])
        request = RequestFactory().post(f"/api/purchase/orders/{self.own.pk}/receive/", data="{}", content_type="application/json")
        request.user = self.manager
        response = receive(request, self.own.pk)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.own.receipts.exists())

    def test_draft_purchase_order_cannot_receive_goods(self):
        from django.test import RequestFactory
        from .api import receive
        self.own.status = PurchaseOrder.Status.DRAFT
        self.own.save(update_fields=["status", "updated_at"])
        request = RequestFactory().post(f"/api/purchase/orders/{self.own.pk}/receive/", data="{}", content_type="application/json")
        request.user = self.manager
        response = receive(request, self.own.pk)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.own.receipts.exists())

    def test_already_received_purchase_order_cannot_receive_again(self):
        from django.test import RequestFactory
        from .api import receive
        self.own.status = PurchaseOrder.Status.RECEIVED
        self.own.save(update_fields=["status", "updated_at"])
        request = RequestFactory().post(f"/api/purchase/orders/{self.own.pk}/receive/", data="{}", content_type="application/json")
        request.user = self.manager
        response = receive(request, self.own.pk)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.own.receipts.exists())
