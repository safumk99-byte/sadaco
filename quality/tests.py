import json

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile


class QualityMutationPermissionTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="quality_staff",
            password="StrongPass123!",
        )
        UserProfile.objects.create(
            user=self.staff_user,
            role=UserProfile.Role.STAFF,
        )
        self.client.force_login(self.staff_user)

    def test_staff_cannot_mutate_quality_records(self):
        requests = [
            ("/api/quality/checks/create/", {"job": 999}),
            ("/api/quality/checks/999/update/", {}),
            ("/api/quality/checks/999/rework/", {}),
            ("/api/quality/rework/999/update/", {}),
            ("/api/quality/jobs/999/packing/", {}),
        ]

        for url, payload in requests:
            with self.subTest(url=url):
                response = self.client.post(
                    url,
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 403)


class QualityReworkLifecycleTests(TestCase):
    def setUp(self):
        from core.models import Department
        from sales.models import Customer, SalesOrder
        from production.models import ProductionJob
        from .models import QualityCheck, ReworkRecord

        department = Department.objects.create(code="quality-lifecycle", name="Quality Lifecycle")
        self.manager = User.objects.create_user(username="quality_manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager,
            role=UserProfile.Role.MANAGER,
            department=department,
        )
        customer = Customer.objects.create(
            name="Quality Customer",
            phone="9000000099",
            department=department,
        )
        order = SalesOrder.objects.create(
            customer=customer,
            item_description="Quality Test Item",
            quantity=1,
            confirmed_price=1000,
        )
        self.job = ProductionJob.objects.create(
            order=order,
            station=ProductionJob.Station.CUSTOM,
            status=ProductionJob.Status.ON_HOLD,
            stage=ProductionJob.Stage.QC_PENDING,
        )
        check = QualityCheck.objects.create(
            job=self.job,
            check_type=QualityCheck.CheckType.FINAL,
            result=QualityCheck.Result.REWORK,
        )
        self.first_rework = ReworkRecord.objects.create(
            quality_check=check,
            job=self.job,
            reason="First issue",
        )
        self.second_rework = ReworkRecord.objects.create(
            quality_check=check,
            job=self.job,
            reason="Second issue",
        )

    def _complete_rework(self, rework):
        return self.client.post(
            f"/api/quality/rework/{rework.pk}/update/",
            data=json.dumps({
                "reason": rework.reason,
                "corrective_action": "Corrected",
                "assigned_staff": "",
                "due_date": "",
                "status": "completed",
            }),
            content_type="application/json",
        )

    def test_job_stays_on_hold_until_all_rework_is_closed(self):
        self.client.force_login(self.manager)
        first = self._complete_rework(self.first_rework)
        self.assertEqual(first.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "on_hold")
        self.assertEqual(self.job.stage, "qc_pending")

        second = self._complete_rework(self.second_rework)
        self.assertEqual(second.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "in_progress")
        self.assertEqual(self.job.stage, "production")

    def test_reopening_rework_keeps_job_on_hold(self):
        self.client.force_login(self.manager)
        self.first_rework.status = "completed"
        self.first_rework.save()
        self.second_rework.status = "completed"
        self.second_rework.save()
        response = self.client.post(
            f"/api/quality/rework/{self.first_rework.pk}/update/",
            data=json.dumps({
                "reason": self.first_rework.reason,
                "corrective_action": "",
                "assigned_staff": "",
                "due_date": "",
                "status": "open",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "on_hold")
        self.assertEqual(self.job.stage, "qc_pending")
