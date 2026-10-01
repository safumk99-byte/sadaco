from django.conf import settings
from django.test import SimpleTestCase


class SystemFoundationTests(SimpleTestCase):
    def test_postgresql_is_configured(self):
        database = settings.DATABASES["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertTrue(database["NAME"])
        self.assertTrue(database["USER"])
        self.assertTrue(database["HOST"])
        self.assertEqual(database["OPTIONS"]["sslmode"], "require")


from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class DashboardTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders_for_authenticated_user(self):
        User.objects.create_user(username="dashboard_user", password="StrongPass123!")
        self.client.login(username="dashboard_user", password="StrongPass123!")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SADACO Dashboard")
