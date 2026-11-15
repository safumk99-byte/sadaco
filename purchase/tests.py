from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from .models import PurchaseOrder, Supplier
from .api import _purchase_orders


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
