import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from accounts.models import UserProfile
from core.models import ApprovalRequest, Department
from .api import approval_thresholds, approval_thresholds_update, expense_create
from .models import ApprovalThreshold, Expense, ExpenseCategory, FinanceTransaction


class FounderApprovalThresholdTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.department = Department.objects.create(code="threshold-test", name="Threshold Test")
        self.manager = User.objects.create_user(username="threshold_manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.founder = User.objects.create_user(username="threshold_founder", password="StrongPass123!")
        UserProfile.objects.create(user=self.founder, role=UserProfile.Role.SUPER_ADMIN)
        self.category = ExpenseCategory.objects.create(name="Threshold Test Expense")

    def post(self, view, user, payload, *args):
        request = self.factory.post("/api/test/", data=json.dumps(payload), content_type="application/json")
        request.user = user
        return view(request, *args)

    def test_only_founder_can_configure_thresholds(self):
        denied = self.post(approval_thresholds_update, self.manager, {"purchase_amount": "5000", "expense_amount": "1000"})
        self.assertEqual(denied.status_code, 403)
        saved = self.post(approval_thresholds_update, self.founder, {"purchase_amount": "5000.00", "expense_amount": "1000.00"})
        self.assertEqual(saved.status_code, 200)
        config = ApprovalThreshold.objects.get()
        self.assertEqual(config.purchase_amount, Decimal("5000.00"))
        self.assertEqual(config.expense_amount, Decimal("1000.00"))
        self.assertEqual(config.updated_by, self.founder)

    def test_thresholds_are_unconfigured_until_founder_sets_them(self):
        request = self.factory.get("/api/finance/approval-thresholds/")
        request.user = self.manager
        response = approval_thresholds(request)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["purchase_amount"])
        self.assertIsNone(response.json()["expense_amount"])
        self.assertFalse(response.json()["configured"])

    def test_paid_expense_is_blocked_when_threshold_is_not_configured(self):
        payload = {
            "category": self.category.pk, "amount": "250.00", "expense_date": date.today().isoformat(),
            "payment_method": "cash", "reference": "", "description": "Test", "status": "paid",
        }
        response = self.post(expense_create, self.manager, payload)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Expense.objects.count(), 0)
        self.assertEqual(FinanceTransaction.objects.count(), 0)

    def test_expense_above_threshold_waits_for_founder_approval(self):
        ApprovalThreshold.objects.create(purchase_amount=Decimal("5000"), expense_amount=Decimal("1000"), updated_by=self.founder)
        payload = {
            "category": self.category.pk, "amount": "1250.00", "expense_date": date.today().isoformat(),
            "payment_method": "cash", "reference": "", "description": "Machine repair", "status": "paid",
            "approval_reason": "Urgent machine repair required for production.",
        }
        response = self.post(expense_create, self.manager, payload)
        self.assertEqual(response.status_code, 202, response.content.decode())
        expense = Expense.objects.get()
        self.assertEqual(expense.status, Expense.Status.DRAFT)
        self.assertEqual(FinanceTransaction.objects.count(), 0)
        approval = ApprovalRequest.objects.get(module="finance", action="pay_expense", reference=expense.expense_no)
        self.assertEqual(approval.status, ApprovalRequest.Status.PENDING)
        self.assertEqual(approval.amount, Decimal("1250.00"))

    def test_founder_approval_posts_expense_transaction_once(self):
        from core.api import approval_review_api
        ApprovalThreshold.objects.create(purchase_amount=Decimal("5000"), expense_amount=Decimal("1000"), updated_by=self.founder)
        payload = {
            "category": self.category.pk, "amount": "1250.00", "expense_date": date.today().isoformat(),
            "payment_method": "cash", "reference": "", "description": "Machine repair", "status": "paid",
            "approval_reason": "Urgent machine repair required for production.",
        }
        self.post(expense_create, self.manager, payload)
        approval = ApprovalRequest.objects.get(module="finance")
        denied = self.post(approval_review_api, self.manager, {"status": "approved"}, approval.pk)
        self.assertEqual(denied.status_code, 403)
        approved = self.post(approval_review_api, self.founder, {"status": "approved", "reviewer_note": "Approved"}, approval.pk)
        self.assertEqual(approved.status_code, 200, approved.content.decode())
        expense = Expense.objects.get()
        self.assertEqual(expense.status, Expense.Status.PAID)
        self.assertEqual(FinanceTransaction.objects.filter(expense=expense).count(), 1)
        repeated = self.post(approval_review_api, self.founder, {"status": "approved"}, approval.pk)
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(FinanceTransaction.objects.filter(expense=expense).count(), 1)
