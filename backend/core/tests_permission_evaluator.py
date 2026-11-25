from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (
    Department, Division, Permission, Role, RolePermission,
    StaffProfile, StaffRole,
)
from .permissions import has_permission


class ScopedRolePermissionTests(TestCase):
    def setUp(self):
        self.division = Division.objects.create(
            code="perm-division", name="Permission Division"
        )
        self.other_division = Division.objects.create(
            code="perm-other", name="Permission Other Division"
        )
        self.department = Department.objects.create(
            division=self.division, name="Design"
        )
        self.other_department = Department.objects.create(
            division=self.division, name="Production"
        )
        user = get_user_model().objects.create_user(
            username="permission-staff", password="test-password-123"
        )
        self.staff = StaffProfile.objects.create(
            user=user, display_name="Permission Staff"
        )
        self.permission = Permission.objects.create(
            code="crm.enquiry.read", description="Read enquiries"
        )
        self.role = Role.objects.create(
            code="crm-reader", name="CRM Reader"
        )
        RolePermission.objects.create(
            role=self.role, permission=self.permission
        )

    def test_permission_is_denied_without_a_configured_role_grant(self):
        self.assertFalse(
            has_permission(
                self.staff, "crm.enquiry.read", division_id=self.division.pk
            )
        )

    def test_division_scoped_role_permission_does_not_cross_divisions(self):
        StaffRole.objects.create(
            staff=self.staff, role=self.role, division=self.division
        )

        self.assertTrue(
            has_permission(
                self.staff, "crm.enquiry.read", division_id=self.division.pk
            )
        )
        self.assertFalse(
            has_permission(
                self.staff, "crm.enquiry.read", division_id=self.other_division.pk
            )
        )

    def test_department_scoped_role_permission_is_limited_to_that_department(self):
        StaffRole.objects.create(
            staff=self.staff, role=self.role, department=self.department
        )

        self.assertTrue(
            has_permission(
                self.staff,
                "crm.enquiry.read",
                division_id=self.division.pk,
                department_id=self.department.pk,
            )
        )
        self.assertFalse(
            has_permission(
                self.staff,
                "crm.enquiry.read",
                division_id=self.division.pk,
                department_id=self.other_department.pk,
            )
        )
        self.assertFalse(
            has_permission(
                self.staff, "crm.enquiry.read", division_id=self.other_division.pk
            )
        )

    def test_expired_and_inactive_role_grants_are_denied(self):
        StaffRole.objects.create(
            staff=self.staff,
            role=self.role,
            division=self.division,
            valid_from=timezone.now() - timezone.timedelta(days=10),
            valid_until=timezone.now() - timezone.timedelta(days=1),
        )
        self.assertFalse(
            has_permission(
                self.staff, "crm.enquiry.read", division_id=self.division.pk
            )
        )

        active_role = Role.objects.create(
            code="crm-reader-active", name="CRM Reader Active"
        )
        RolePermission.objects.create(
            role=active_role, permission=self.permission
        )
        StaffRole.objects.create(
            staff=self.staff, role=active_role, division=self.division
        )
        self.staff.employment_status = StaffProfile.EmploymentStatus.INACTIVE
        self.staff.save(update_fields=["employment_status"])
        self.assertFalse(
            has_permission(
                self.staff, "crm.enquiry.read", division_id=self.division.pk
            )
        )

    def test_global_founder_retains_cross_division_permission(self):
        founder_role = Role.objects.create(
            code="founder", name="Founder"
        )
        StaffRole.objects.create(
            staff=self.staff, role=founder_role
        )

        self.assertTrue(
            has_permission(
                self.staff, "any.unconfigured.permission",
                division_id=self.other_division.pk,
            )
        )
