from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.urls import reverse

from accounts.models import UserProfile
from core.models import Department
from .models import Designation, PerformanceRecord, StaffAttendance, StaffProfile, StaffTask, WorkArea


class StaffModuleTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="staff-module-test", name="Staff Module Test")
        self.admin = User.objects.create_user(username="manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.admin,
            role=UserProfile.Role.MANAGER,
            department=self.department,
        )
        self.designation = Designation.objects.create(name="Manager")
        self.area = WorkArea.objects.create(name="Administration")
        self.staff_user = User.objects.create_user(
            username="staff01",
            password="StrongPass123!",
            first_name="Test",
            last_name="Staff",
        )
        UserProfile.objects.create(user=self.staff_user, role=UserProfile.Role.STAFF, department=self.department)
        self.staff = StaffProfile.objects.create(
            user=self.staff_user,
            staff_id="ST001",
            department=self.department,
            designation=self.designation,
            work_area=self.area,
        )

    def test_staff_list_requires_login(self):
        response = self.client.get(reverse("staff:list"))
        self.assertEqual(response.status_code, 302)

    def test_manager_can_view_staff(self):
        self.client.login(username="manager", password="StrongPass123!")
        response = self.client.get(reverse("staff:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ST001")

    def test_staff_can_view_own_profile(self):
        self.client.login(username="staff01", password="StrongPass123!")
        response = self.client.get(reverse("staff:detail", args=[self.staff.id]))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_open_management_create(self):
        self.client.login(username="staff01", password="StrongPass123!")
        response = self.client.get(reverse("staff:create"))
        self.assertEqual(response.status_code, 403)

    def test_unique_attendance_per_day(self):
        from .forms import AttendanceForm
        StaffAttendance.objects.create(
            staff=self.staff,
            date=date(2026, 8, 18),
            status=StaffAttendance.Status.PRESENT,
        )
        form = AttendanceForm(data={
            "staff": self.staff.pk,
            "date": "2026-08-18",
            "status": "absent",
            "remarks": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("already exists", str(form.errors))

    def test_staff_sees_only_own_dashboard_counts(self):
        other_user = User.objects.create_user(username="staff02", password="StrongPass123!")
        UserProfile.objects.create(user=other_user, role=UserProfile.Role.STAFF)
        StaffProfile.objects.create(user=other_user, staff_id="ST002")
        self.client.login(username="staff01", password="StrongPass123!")
        response = self.client.get(reverse("staff:list"))
        self.assertEqual(response.context["stats"]["total_staff"], 1)

    def test_completed_task_gets_completion_timestamp(self):
        self.client.login(username="manager", password="StrongPass123!")
        response = self.client.post(reverse("staff:task_create"), {
            "title": "Finish report",
            "description": "",
            "assigned_to": self.staff.pk,
            "due_date": "2026-08-18",
            "priority": "medium",
            "status": "completed",
            "remarks": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(StaffTask.objects.get(title="Finish report").completed_at)


class StaffOperationalRegressionTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="staff-ops-test", name="Staff Ops Test")
        self.manager = User.objects.create_user(
            username="opsmanager", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.designation = Designation.objects.create(name="Operations")
        self.area = WorkArea.objects.create(name="Operations Area")
        self.staff_user = User.objects.create_user(
            username="opsstaff", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.staff_user, role=UserProfile.Role.STAFF, department=self.department)
        self.staff = StaffProfile.objects.create(
            user=self.staff_user,
            staff_id="OPS001",
            department=self.department,
            designation=self.designation,
            work_area=self.area,
        )

    def test_staff_create_accepts_uploaded_photo(self):
        self.client.login(username="opsmanager", password="StrongPass123!")
        buffer = BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        image = SimpleUploadedFile(
            "staff.png",
            buffer.getvalue(),
            content_type="image/png",
        )
        # The file content is intentionally tiny; form binding should still receive it.
        form_data = {
            "username": "newstaff",
            "password": "StrongPass123!",
            "first_name": "New",
            "last_name": "Staff",
            "email": "",
            "staff_id": "OPS002",
            "designation": self.designation.pk,
            "work_area": self.area.pk,
            "phone": "",
            "joining_date": "",
            "address": "",
            "status": "active",
        }
        response = self.client.post(
            reverse("staff:create"), data={**form_data, "photo": image}
        )
        self.assertEqual(response.status_code, 302)
        created = StaffProfile.objects.get(staff_id="OPS002")
        self.assertTrue(bool(created.photo.name))

    def test_completed_task_on_create_sets_timestamp(self):
        self.client.login(username="opsmanager", password="StrongPass123!")
        response = self.client.post(reverse("staff:task_create"), {
            "title": "Completed immediately",
            "description": "",
            "assigned_to": self.staff.pk,
            "due_date": "2026-08-18",
            "priority": "medium",
            "status": "completed",
            "remarks": "",
        })
        self.assertEqual(response.status_code, 302)
        task = StaffTask.objects.get(title="Completed immediately")
        self.assertIsNotNone(task.completed_at)

    def test_staff_cannot_mark_attendance(self):
        self.client.login(username="opsstaff", password="StrongPass123!")
        response = self.client.get(reverse("staff:attendance_create"))
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_create_performance(self):
        self.client.login(username="opsstaff", password="StrongPass123!")
        response = self.client.get(reverse("staff:performance_create"))
        self.assertEqual(response.status_code, 403)


class StaffMediaRegressionTests(TestCase):
    def test_media_url_is_root_relative(self):
        from django.conf import settings
        self.assertEqual(settings.MEDIA_URL, "/media/")

    def test_staff_photo_url_is_media_based(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image

        user = User.objects.create_user(
            username="photo_user", password="StrongPass123!"
        )
        UserProfile.objects.create(user=user, role=UserProfile.Role.STAFF)

        buffer = BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        image = SimpleUploadedFile(
            "profile.png", buffer.getvalue(), content_type="image/png"
        )
        profile = StaffProfile.objects.create(
            user=user,
            staff_id="PHOTO001",
            photo=image,
        )
        self.assertTrue(profile.photo.url.startswith("/media/"))


class DepartmentAccessScopeTests(TestCase):
    def setUp(self):
        from staff.services import (
            staff_for_user, task_queryset_for_user,
            attendance_queryset_for_user, performance_queryset_for_user,
            dashboard_stats,
        )
        self.staff_for_user = staff_for_user
        self.task_queryset_for_user = task_queryset_for_user
        self.attendance_queryset_for_user = attendance_queryset_for_user
        self.performance_queryset_for_user = performance_queryset_for_user
        self.dashboard_stats = dashboard_stats

        self.creatives = Department.objects.get_or_create(code="creatives", defaults={"name": "SADACO Creatives"})[0]
        self.cnc = Department.objects.get_or_create(code="cnc", defaults={"name": "SADACO CNC"})[0]
        self.manager_user = User.objects.create_user(username="creative_manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager_user, role=UserProfile.Role.MANAGER, department=self.creatives
        )
        self.other_manager_user = User.objects.create_user(username="cnc_manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.other_manager_user, role=UserProfile.Role.MANAGER, department=self.cnc
        )
        self.creative_user = User.objects.create_user(username="creative_staff", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.creative_user, role=UserProfile.Role.STAFF, department=self.creatives
        )
        self.cnc_user = User.objects.create_user(username="cnc_staff", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.cnc_user, role=UserProfile.Role.STAFF, department=self.cnc
        )
        self.creative_staff = StaffProfile.objects.create(
            user=self.creative_user, staff_id="CRE-001", department=self.creatives
        )
        self.cnc_staff = StaffProfile.objects.create(
            user=self.cnc_user, staff_id="CNC-001", department=self.cnc
        )

    def test_manager_sees_only_staff_in_own_department(self):
        ids = set(self.staff_for_user(self.manager_user).values_list("id", flat=True))
        self.assertEqual(ids, {self.creative_staff.id})

    def test_manager_sees_only_own_department_tasks_attendance_and_performance(self):
        creative_task = StaffTask.objects.create(title="Creative task", assigned_to=self.creative_staff)
        StaffTask.objects.create(title="CNC task", assigned_to=self.cnc_staff)
        creative_attendance = StaffAttendance.objects.create(
            staff=self.creative_staff, date=date(2026, 11, 1), status=StaffAttendance.Status.PRESENT
        )
        StaffAttendance.objects.create(
            staff=self.cnc_staff, date=date(2026, 11, 1), status=StaffAttendance.Status.PRESENT
        )
        creative_review = PerformanceRecord.objects.create(
            staff=self.creative_staff, review_date=date(2026, 11, 1), score=90
        )
        PerformanceRecord.objects.create(
            staff=self.cnc_staff, review_date=date(2026, 11, 1), score=70
        )
        self.assertEqual(list(self.task_queryset_for_user(self.manager_user)), [creative_task])
        self.assertEqual(list(self.attendance_queryset_for_user(self.manager_user)), [creative_attendance])
        self.assertEqual(list(self.performance_queryset_for_user(self.manager_user)), [creative_review])

    def test_manager_without_department_has_no_cross_department_staff_access(self):
        unassigned = User.objects.create_user(username="unassigned_manager", password="StrongPass123!")
        UserProfile.objects.create(user=unassigned, role=UserProfile.Role.MANAGER)
        self.assertFalse(self.staff_for_user(unassigned).exists())
        self.assertFalse(self.task_queryset_for_user(unassigned).exists())
        self.assertEqual(self.dashboard_stats(unassigned)["total_staff"], 0)

    def test_global_admin_can_view_staff_across_departments(self):
        admin = User.objects.create_superuser(username="root_admin", password="StrongPass123!")
        ids = set(self.staff_for_user(admin).values_list("id", flat=True))
        self.assertEqual(ids, {self.creative_staff.id, self.cnc_staff.id})
