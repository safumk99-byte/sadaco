import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from accounts.models import UserProfile
from core.models import ApprovalRequest, Department
from finance.models import ApprovalThreshold
from products.models import MaterialVariant
from .api import create
from .models import PurchaseOrder, Supplier


class PurchaseApprovalThresholdTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.department = Department.objects.create(code="purchase-threshold", name="Purchase Threshold")
        self.manager = User.objects.create_user(username="purchase_threshold_manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.founder = User.objects.create_user(username="purchase_threshold_founder", password="StrongPass123!")
        UserProfile.objects.create(user=self.founder, role=UserProfile.Role.SUPER_ADMIN)
        self.supplier = Supplier.objects.create(name="Threshold Supplier")
        self.material = MaterialVariant.objects.create(
            material_name="Threshold Acrylic", brand="Test", thickness_mm=Decimal("3"),
            purchase_rate=Decimal("80"), unit="Sheet",
        )

    def post(self, view, user, payload, *args):
        request = self.factory.post("/api/purchase/orders/create/", data=json.dumps(payload), content_type="application/json")
        request.user = user
        return view(request, *args)

    def test_sent_purchase_order_is_blocked_until_threshold_is_configured(self):
        response = self.post(create, self.manager, {
            "supplier": self.supplier.pk, "order_date": date.today().isoformat(), "status": "sent",
            "discount": "0", "tax": "0", "notes": "", "material_variant": self.material.pk,
            "quantity": "2", "unit_cost": "1000",
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_purchase_order_above_threshold_stays_draft_until_founder_approval(self):
        ApprovalThreshold.objects.create(purchase_amount=Decimal("1500"), expense_amount=Decimal("1000"), updated_by=self.founder)
        response = self.post(create, self.manager, {
            "supplier": self.supplier.pk, "order_date": date.today().isoformat(), "status": "sent",
            "discount": "0", "tax": "0", "notes": "", "material_variant": self.material.pk,
            "quantity": "2", "unit_cost": "1000", "approval_reason": "Required acrylic stock for confirmed production jobs.",
        })
        self.assertEqual(response.status_code, 202, response.content.decode())
        order = PurchaseOrder.objects.get()
        self.assertEqual(order.total, Decimal("2000.00"))
        self.assertEqual(order.status, PurchaseOrder.Status.DRAFT)
        approval = ApprovalRequest.objects.get(module="purchase", action="send_purchase_order", reference=order.po_no)
        self.assertEqual(approval.status, ApprovalRequest.Status.PENDING)

    def test_founder_approval_sends_purchase_order_and_rejection_leaves_draft(self):
        from core.api import approval_review_api
        ApprovalThreshold.objects.create(purchase_amount=Decimal("1500"), expense_amount=Decimal("1000"), updated_by=self.founder)
        self.post(create, self.manager, {
            "supplier": self.supplier.pk, "order_date": date.today().isoformat(), "status": "sent",
            "discount": "0", "tax": "0", "notes": "", "material_variant": self.material.pk,
            "quantity": "2", "unit_cost": "1000", "approval_reason": "Required acrylic stock for confirmed production jobs.",
        })
        approval = ApprovalRequest.objects.get(module="purchase")
        rejected = self.post(approval_review_api, self.founder, {"status": "rejected", "reviewer_note": "Budget review required."}, approval.pk)
        self.assertEqual(rejected.status_code, 200, rejected.content.decode())
        order = PurchaseOrder.objects.get()
        self.assertEqual(order.status, PurchaseOrder.Status.DRAFT)
