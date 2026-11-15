from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from purchase.models import PurchaseOrder, Supplier
from sales.models import Customer, SalesOrder
from .models import Expense, ExpenseCategory
from .api import _department_expenses, _department_orders, _department_purchase_orders


class FinanceDepartmentAccessTests(TestCase):
    def setUp(self):
        self.a = Department.objects.create(code="finance-a", name="Finance A")
        self.b = Department.objects.create(code="finance-b", name="Finance B")
        self.manager = User.objects.create_user(username="finance_a_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.a)
        self.other = User.objects.create_user(username="finance_b_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other, role=UserProfile.Role.MANAGER, department=self.b)
        category = ExpenseCategory.objects.create(name="Test Expense")
        self.own_expense = Expense.objects.create(category=category, amount=100, created_by=self.manager)
        Expense.objects.create(category=category, amount=200, created_by=self.other)
        own_customer = Customer.objects.create(name="Finance A Customer", phone="9000000011", department=self.a)
        other_customer = Customer.objects.create(name="Finance B Customer", phone="9000000012", department=self.b)
        self.own_order = SalesOrder.objects.create(customer=own_customer, item_description="A", quantity=1, confirmed_price=1000)
        SalesOrder.objects.create(customer=other_customer, item_description="B", quantity=1, confirmed_price=2000)
        supplier = Supplier.objects.create(name="Finance Supplier")
        self.own_po = PurchaseOrder.objects.create(supplier=supplier, created_by=self.manager)
        PurchaseOrder.objects.create(supplier=supplier, created_by=self.other)

    def test_manager_finance_queries_are_department_scoped(self):
        self.assertEqual(set(_department_expenses(self.manager).values_list("id", flat=True)), {self.own_expense.id})
        self.assertEqual(set(_department_orders(self.manager).values_list("id", flat=True)), {self.own_order.id})
        self.assertEqual(set(_department_purchase_orders(self.manager).values_list("id", flat=True)), {self.own_po.id})

    def test_global_admin_sees_all_finance_records(self):
        admin = User.objects.create_superuser(username="finance_root", password="StrongPass123!")
        self.assertEqual(_department_expenses(admin).count(), 2)
        self.assertEqual(_department_orders(admin).count(), 2)
        self.assertEqual(_department_purchase_orders(admin).count(), 2)
