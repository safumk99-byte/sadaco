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


class DepartmentManagementTests(TestCase):
    def setUp(self):
        from accounts.models import UserProfile
        self.admin = User.objects.create_superuser(
            username="division_admin", email="admin@example.test", password="StrongPass123!"
        )
        self.client.force_login(self.admin)
        self.manager = User.objects.create_user(
            username="creatives_manager", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)

    def test_seeded_sadaco_divisions_exist(self):
        from core.models import Department
        self.assertTrue(Department.objects.filter(code="creatives", name="SADACO Creatives").exists())
        self.assertTrue(Department.objects.filter(code="cnc", name="SADACO CNC").exists())
        self.assertTrue(Department.objects.filter(code="decor", name="SADACO Decor Co.").exists())

    def test_department_list_requires_login(self):
        self.client.logout()
        response = self.client.get("/api/departments/")
        self.assertEqual(response.status_code, 302)

    def test_admin_can_create_department(self):
        import json
        response = self.client.post(
            "/api/departments/create/",
            data=json.dumps({"code": "testing", "name": "SADACO Test Division"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_assigning_manager_syncs_user_department(self):
        import json
        from core.models import Department
        from accounts.models import UserProfile
        department = Department.objects.get(code="creatives")
        response = self.client.post(
            f"/api/departments/{department.pk}/update/",
            data=json.dumps({"manager": self.manager.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.manager.profile.refresh_from_db()
        self.assertEqual(self.manager.profile.department_id, department.pk)

    def test_regular_staff_cannot_manage_departments(self):
        import json
        from accounts.models import UserProfile
        staff_user = User.objects.create_user(username="division_staff", password="StrongPass123!")
        UserProfile.objects.create(user=staff_user, role=UserProfile.Role.STAFF)
        self.client.force_login(staff_user)
        response = self.client.post(
            "/api/departments/create/",
            data=json.dumps({"code": "forbidden", "name": "Forbidden Division"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
