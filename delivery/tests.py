import json

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from sales.models import Customer, DeliveryRecord, SalesOrder


class DeliveryLifecycleTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="delivery-qa", name="Delivery QA")
        self.manager = User.objects.create_user(username="delivery_manager", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager,
            role=UserProfile.Role.MANAGER,
            department=self.department,
        )
        customer = Customer.objects.create(
            name="Delivery Customer",
            phone="9000000077",
            department=self.department,
        )
        self.order = SalesOrder.objects.create(
            customer=customer,
            item_description="Delivery Test Item",
            quantity=1,
            confirmed_price=1000,
            status=SalesOrder.Status.CONFIRMED,
        )
        self.client.force_login(self.manager)

    def _update(self, payload):
        return self.client.post(
            f"/api/delivery/orders/{self.order.pk}/update/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_cannot_dispatch_order_before_final_qc_ready(self):
        response = self._update({"status": DeliveryRecord.Status.OUT})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(DeliveryRecord.objects.filter(order=self.order).exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.CONFIRMED)

    def test_cannot_mark_order_delivered_before_final_qc_ready(self):
        response = self._update({"status": DeliveryRecord.Status.DELIVERED})
        self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.CONFIRMED)

    def test_ready_order_can_be_dispatched_and_delivered(self):
        self.order.status = SalesOrder.Status.READY
        self.order.save(update_fields=["status", "updated_at"])
        scheduled = self._update({"status": DeliveryRecord.Status.SCHEDULED})
        self.assertEqual(scheduled.status_code, 200)
        dispatched = self._update({"status": DeliveryRecord.Status.OUT})
        self.assertEqual(dispatched.status_code, 200)
        delivered = self._update({"status": DeliveryRecord.Status.DELIVERED})
        self.assertEqual(delivered.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.DELIVERED)

    def test_delivered_order_cannot_be_rewound_to_scheduled(self):
        self.order.status = SalesOrder.Status.DELIVERED
        self.order.save(update_fields=["status", "updated_at"])
        DeliveryRecord.objects.create(order=self.order, status=DeliveryRecord.Status.DELIVERED)
        response = self._update({"status": DeliveryRecord.Status.SCHEDULED})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DeliveryRecord.objects.get(order=self.order).status, DeliveryRecord.Status.DELIVERED)

    def test_installed_requires_installation_flag(self):
        self.order.status = SalesOrder.Status.READY
        self.order.save(update_fields=["status", "updated_at"])
        DeliveryRecord.objects.create(order=self.order, status=DeliveryRecord.Status.OUT)
        response = self._update({"status": DeliveryRecord.Status.INSTALLED})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(DeliveryRecord.objects.get(order=self.order).status, DeliveryRecord.Status.OUT)

    def test_feedback_rating_must_be_between_one_and_five(self):
        response = self.client.post(
            f"/api/delivery/orders/{self.order.pk}/feedback/",
            data=json.dumps({"rating": 8, "comment": "Invalid rating"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


    def test_feedback_cannot_be_recorded_before_delivery(self):
        response = self.client.post(
            f"/api/delivery/orders/{self.order.pk}/feedback/",
            data=json.dumps({"rating": 5, "comment": "Premature feedback"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        from sales.models import CustomerFeedback
        self.assertFalse(CustomerFeedback.objects.filter(order=self.order).exists())
