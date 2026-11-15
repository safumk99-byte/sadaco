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
