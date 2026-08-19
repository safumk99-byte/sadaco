from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image
from django.urls import reverse

from accounts.models import UserProfile
from .models import Designation, StaffAttendance, StaffProfile, StaffTask, WorkArea


class StaffModuleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.admin,
            role=UserProfile.Role.MANAGER,
        )
        self.designation = Designation.objects.create(name="Manager")
        self.area = WorkArea.objects.create(name="Administration")
        self.staff_user = User.objects.create_user(
            username="staff01",
            password="StrongPass123!",
            first_name="Test",
            last_name="Staff",
        )
        UserProfile.objects.create(user=self.staff_user, role=UserProfile.Role.STAFF)
        self.staff = StaffProfile.objects.create(
            user=self.staff_user,
            staff_id="ST001",
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
        self.manager = User.objects.create_user(
            username="opsmanager", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.designation = Designation.objects.create(name="Operations")
        self.area = WorkArea.objects.create(name="Operations Area")
        self.staff_user = User.objects.create_user(
            username="opsstaff", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.staff_user, role=UserProfile.Role.STAFF)
        self.staff = StaffProfile.objects.create(
            user=self.staff_user,
            staff_id="OPS001",
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
