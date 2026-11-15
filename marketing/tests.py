from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from sales.models import Customer
from .models import Campaign, MarketingContent, MarketingLead
from .api_views import _campaigns, _contents, _leads


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

    def test_content_created_here_cannot_expose_foreign_campaign(self):
        foreign_campaign = Campaign.objects.get(name="Campaign B")
        content = MarketingContent.objects.create(title="Legacy content", channel="Social", campaign=foreign_campaign, created_by=self.manager)
        self.assertFalse(_contents(self.manager).filter(pk=content.pk).exists())

    def test_lead_created_here_cannot_expose_foreign_customer(self):
        foreign_customer = Customer.objects.create(name="Foreign Customer", phone="9000000099", department=self.b)
        lead = MarketingLead.objects.create(source="Legacy import", customer=foreign_customer, created_by=self.manager)
        self.assertFalse(_leads(self.manager).filter(pk=lead.pk).exists())


    def test_campaign_create_rejects_invalid_date_range_and_negative_budget(self):
        import json
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/marketing/campaigns/create/",
            data=json.dumps({
                "name": "Invalid campaign",
                "channel": "Social",
                "start_date": "2026-12-10",
                "end_date": "2026-12-01",
                "budget": "-10",
                "status": "planned",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Campaign.objects.filter(name="Invalid campaign").exists())

    def test_campaign_create_rejects_unknown_status(self):
        import json
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/marketing/campaigns/create/",
            data=json.dumps({
                "name": "Unknown status campaign",
                "channel": "Social",
                "budget": "0",
                "status": "made_up",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Campaign.objects.filter(name="Unknown status campaign").exists())

    def test_lead_create_rejects_foreign_department_customer(self):
        import json
        foreign = Customer.objects.create(name="Foreign Lead Customer", phone="9000000098", department=self.b)
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/marketing/leads/create/",
            data=json.dumps({"source": "Referral", "customer": foreign.pk, "status": "new"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, (400, 404))
        self.assertFalse(MarketingLead.objects.filter(customer=foreign).exists())
