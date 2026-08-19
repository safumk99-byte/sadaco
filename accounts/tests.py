from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import UserProfile, role_group_name, sync_role_group

class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="StrongPass123!")
        UserProfile.objects.create(user=self.user, role=UserProfile.Role.INSTITUTION_ADMIN)

    def test_login_page(self):
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)

    def test_login_success(self):
        self.assertTrue(self.client.login(username="admin", password="StrongPass123!"))

    def test_user_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 302)

    def test_admin_user_list(self):
        self.client.login(username="admin", password="StrongPass123!")
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 200)

    def test_role_group_sync(self):
        sync_role_group(self.user, UserProfile.Role.INSTITUTION_ADMIN)
        self.assertTrue(self.user.groups.filter(name=role_group_name(UserProfile.Role.INSTITUTION_ADMIN)).exists())


class UserRoleSecurityTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="superadmin", password="StrongPass123!"
        )
        UserProfile.objects.create(
            user=self.super_admin, role=UserProfile.Role.SUPER_ADMIN
        )
        self.institution_admin = User.objects.create_user(
            username="institutionadmin", password="StrongPass123!"
        )
        UserProfile.objects.create(
            user=self.institution_admin, role=UserProfile.Role.INSTITUTION_ADMIN
        )
        self.manager = User.objects.create_user(
            username="manager", password="StrongPass123!"
        )
        UserProfile.objects.create(
            user=self.manager, role=UserProfile.Role.MANAGER
        )
        self.staff = User.objects.create_user(
            username="staffuser", password="StrongPass123!"
        )
        UserProfile.objects.create(
            user=self.staff, role=UserProfile.Role.STAFF
        )

    def test_institution_admin_cannot_edit_super_admin(self):
        self.client.login(username="institutionadmin", password="StrongPass123!")
        response = self.client.get(
            reverse("accounts:user_edit", kwargs={"user_id": self.super_admin.id})
        )
        self.assertEqual(response.status_code, 403)

    def test_institution_admin_can_manage_staff(self):
        self.client.login(username="institutionadmin", password="StrongPass123!")
        response = self.client.get(
            reverse("accounts:user_edit", kwargs={"user_id": self.staff.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_open_user_management(self):
        self.client.login(username="manager", password="StrongPass123!")
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_deactivate_self(self):
        self.client.login(username="institutionadmin", password="StrongPass123!")
        response = self.client.post(
            reverse("accounts:user_edit", kwargs={"user_id": self.institution_admin.id}),
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone": "",
                "role": UserProfile.Role.INSTITUTION_ADMIN,
                "is_active": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.institution_admin.refresh_from_db()
        self.assertTrue(self.institution_admin.is_active)

    def test_role_group_stays_in_sync_after_edit(self):
        self.client.login(username="institutionadmin", password="StrongPass123!")
        response = self.client.post(
            reverse("accounts:user_edit", kwargs={"user_id": self.staff.id}),
            {
                "first_name": "Updated",
                "last_name": "Staff",
                "email": "staff@example.com",
                "phone": "9999999999",
                "role": UserProfile.Role.MANAGER,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.staff.refresh_from_db()
        self.assertTrue(
            self.staff.groups.filter(
                name=role_group_name(UserProfile.Role.MANAGER)
            ).exists()
        )
