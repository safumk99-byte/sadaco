from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from marketing.models import Campaign, MarketingLead
from sales.models import Customer
from .api_views import _department_leads


class ReportsDepartmentAccessTests(TestCase):
    def setUp(self):
        self.a = Department.objects.create(code="reports-a", name="Reports A")
        self.b = Department.objects.create(code="reports-b", name="Reports B")
        self.manager = User.objects.create_user(username="reports_a_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.a)
        self.other_manager = User.objects.create_user(username="reports_b_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other_manager, role=UserProfile.Role.MANAGER, department=self.b)
        self.foreign_customer = Customer.objects.create(
            name="Foreign Reports Customer", phone="9000000201", department=self.b
        )
        self.foreign_campaign = Campaign.objects.create(
            name="Foreign Reports Campaign", channel="Social", created_by=self.other_manager
        )

    def test_report_lead_cannot_expose_foreign_customer_when_created_in_own_department(self):
        lead = MarketingLead.objects.create(
            source="Legacy", customer=self.foreign_customer, created_by=self.manager
        )
        self.assertFalse(_department_leads(self.manager).filter(pk=lead.pk).exists())

    def test_report_lead_cannot_expose_foreign_campaign_when_created_in_own_department(self):
        lead = MarketingLead.objects.create(
            source="Legacy", campaign=self.foreign_campaign, created_by=self.manager
        )
        self.assertFalse(_department_leads(self.manager).filter(pk=lead.pk).exists())

    def test_global_admin_sees_leads_across_departments(self):
        MarketingLead.objects.create(
            source="Foreign", customer=self.foreign_customer, created_by=self.other_manager
        )
        admin = User.objects.create_superuser(username="reports_root", password="StrongPass123!")
        self.assertEqual(_department_leads(admin).count(), 1)
