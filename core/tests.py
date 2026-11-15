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
from accounts.models import UserProfile
from core.models import Department
from sales.models import Customer, OrderRequest
from core.models import ApprovalRequest


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


class CustomerRequestDepartmentAccessTests(TestCase):
    def setUp(self):
        self.a = Department.objects.create(code="requests-a", name="Requests A")
        self.b = Department.objects.create(code="requests-b", name="Requests B")
        self.manager = User.objects.create_user(username="request_a_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.a)
        self.other_manager = User.objects.create_user(username="request_b_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other_manager, role=UserProfile.Role.MANAGER, department=self.b)
        self.customer_a = Customer.objects.create(name="Request Customer A", phone="9000000101", department=self.a)
        self.customer_b = Customer.objects.create(name="Request Customer B", phone="9000000102", department=self.b)
        self.request_a = OrderRequest.objects.create(
            customer=self.customer_a, quantity=1, requirement="A request", assigned_to=self.manager
        )
        self.request_b = OrderRequest.objects.create(
            customer=self.customer_b, quantity=1, requirement="B request", assigned_to=self.other_manager
        )

    def test_manager_sees_only_own_department_customer_requests(self):
        self.client.force_login(self.manager)
        response = self.client.get("/api/customer-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([x["id"] for x in response.json()["items"]], [self.request_a.id])

    def test_regular_customer_cannot_read_internal_request_queue(self):
        customer_user = User.objects.create_user(username="portal_customer", password="StrongPass123!")
        Customer.objects.create(user=customer_user, name="Portal Customer", phone="9000000103")
        self.client.force_login(customer_user)
        response = self.client.get("/api/customer-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])

    def test_assigned_staff_cannot_edit_manager_notes(self):
        staff_user = User.objects.create_user(username="request_a_staff", password="StrongPass123!")
        UserProfile.objects.create(
            user=staff_user, role=UserProfile.Role.STAFF, department=self.a
        )
        item = OrderRequest.objects.create(
            customer=self.customer_a,
            quantity=1,
            requirement="Staff request",
            assigned_to=staff_user,
            manager_notes="Private manager note",
        )
        self.client.force_login(staff_user)
        response = self.client.post(
            f"/api/customer-requests/{item.pk}/update/",
            data='{"status":"contacted","manager_notes":"Tampered note"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.manager_notes, "Private manager note")


class ApprovalDepartmentAccessTests(TestCase):
    def setUp(self):
        self.a = Department.objects.create(code="approval-a", name="Approval A")
        self.b = Department.objects.create(code="approval-b", name="Approval B")
        self.manager = User.objects.create_user(username="approval_a_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.a)
        self.other_manager = User.objects.create_user(username="approval_b_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other_manager, role=UserProfile.Role.MANAGER, department=self.b)
        self.own_request = ApprovalRequest.objects.create(
            module="finance", action="expense", reason="Own division request", requested_by=self.manager
        )
        self.foreign_request = ApprovalRequest.objects.create(
            module="finance", action="expense", reason="Other division request", requested_by=self.other_manager
        )

    def test_manager_lists_only_own_department_approvals(self):
        self.client.force_login(self.manager)
        response = self.client.get("/api/approvals/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["items"]], [self.own_request.id])

    def test_manager_cannot_review_another_department_approval(self):
        import json
        self.client.force_login(self.manager)
        response = self.client.post(
            f"/api/approvals/{self.foreign_request.pk}/review/",
            data=json.dumps({"status": "approved", "reviewer_note": "Not my division"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.foreign_request.refresh_from_db()
        self.assertEqual(self.foreign_request.status, ApprovalRequest.Status.PENDING)
        self.assertIsNone(self.foreign_request.reviewed_by_id)
