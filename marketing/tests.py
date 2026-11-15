from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from .models import Campaign
from .api_views import _campaigns


class MarketingDepartmentAccessTests(TestCase):
    def setUp(self):
        self.a = Department.objects.create(code="marketing-a", name="Marketing A")
        self.b = Department.objects.create(code="marketing-b", name="Marketing B")
        self.manager = User.objects.create_user(username="marketing_a_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.a)
        self.other = User.objects.create_user(username="marketing_b_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other, role=UserProfile.Role.MANAGER, department=self.b)
        self.own = Campaign.objects.create(name="Campaign A", channel="Social", created_by=self.manager)
        Campaign.objects.create(name="Campaign B", channel="Social", created_by=self.other)

    def test_manager_sees_only_own_department_campaigns(self):
        self.assertEqual(set(_campaigns(self.manager).values_list("id", flat=True)), {self.own.id})

    def test_global_admin_sees_all_campaigns(self):
        admin = User.objects.create_superuser(username="marketing_root", password="StrongPass123!")
        self.assertEqual(_campaigns(admin).count(), 2)

    def test_unassigned_manager_sees_no_campaigns(self):
        user = User.objects.create_user(username="marketing_unassigned", password="StrongPass123!")
        UserProfile.objects.create(user=user, role=UserProfile.Role.MANAGER)
        self.assertFalse(_campaigns(user).exists())
