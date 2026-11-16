import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from accounts.models import UserProfile
from core.models import Department
from purchase.models import PurchaseOrder, Supplier
from .api import supplier_payment_create
from .models import FinanceTransaction, SupplierPayment


class DraftPurchaseSupplierPaymentGuardTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.department = Department.objects.create(code="supplier-payment-guard", name="Supplier Payment Guard")
        self.manager = User.objects.create_user(username="supplier_payment_guard", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.supplier = Supplier.objects.create(name="Draft PO Supplier")
        self.order = PurchaseOrder.objects.create(
            supplier=self.supplier, department=self.department, created_by=self.manager,
            status=PurchaseOrder.Status.DRAFT, subtotal=Decimal("1000"),
        )

    def test_supplier_payment_cannot_be_paid_against_draft_purchase_order(self):
        request = self.factory.post("/api/finance/supplier-payments/create/", data=json.dumps({
            "purchase_order": self.order.pk, "amount": "100", "payment_date": date.today().isoformat(),
            "payment_method": "cash", "reference": "", "status": "paid", "notes": "",
        }), content_type="application/json")
        request.user = self.manager
        response = supplier_payment_create(request)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(SupplierPayment.objects.count(), 0)
        self.assertEqual(FinanceTransaction.objects.count(), 0)
