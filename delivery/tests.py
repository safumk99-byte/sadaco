import json

from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from core.models import Department
from sales.models import Customer, DeliveryRecord, SalesOrder, PaymentRecord


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

    def _complete_packing(self):
        from production.models import ProductionJob
        from quality.models import PackingRecord
        job = ProductionJob.objects.create(
            order=self.order,
            station=ProductionJob.Station.CUSTOM,
            status=ProductionJob.Status.COMPLETED,
            stage=ProductionJob.Stage.COMPLETED,
        )
        PackingRecord.objects.create(job=job, status=PackingRecord.Status.PACKED)
        return job

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
        PaymentRecord.objects.create(
            order=self.order, payment_type=PaymentRecord.PaymentType.ADVANCE,
            amount=500, status=PaymentRecord.Status.RECEIVED,
        )
        PaymentRecord.objects.create(
            order=self.order, payment_type=PaymentRecord.PaymentType.FINAL,
            amount=500, status=PaymentRecord.Status.RECEIVED,
        )
        self.order.status = SalesOrder.Status.READY
        self.order.save(update_fields=["status", "updated_at"])
        self._complete_packing()
        scheduled = self._update({"status": DeliveryRecord.Status.SCHEDULED})
        self.assertEqual(scheduled.status_code, 200)
        dispatched = self._update({"status": DeliveryRecord.Status.OUT})
        self.assertEqual(dispatched.status_code, 200)
        delivered = self._update({"status": DeliveryRecord.Status.DELIVERED})
        self.assertEqual(delivered.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, SalesOrder.Status.DELIVERED)


    def test_dispatch_is_blocked_until_full_payment_or_founder_credit_exception(self):
        self.order.status = SalesOrder.Status.READY
        self.order.save(update_fields=["status", "updated_at"])
        DeliveryRecord.objects.create(order=self.order, status=DeliveryRecord.Status.SCHEDULED)
        response = self._update({"status": DeliveryRecord.Status.OUT})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Final payment", response.json()["detail"])
        self.assertEqual(DeliveryRecord.objects.get(order=self.order).status, DeliveryRecord.Status.SCHEDULED)

    def test_founder_credit_exception_allows_dispatch_with_balance(self):
        founder = User.objects.create_superuser(username="delivery_founder", password="StrongPass123!")
        self.order.status = SalesOrder.Status.READY
        self.order.credit_exception_reason = "Approved customer credit terms"
        self.order.credit_exception_approved_by = founder
        from django.utils import timezone
        self.order.credit_exception_approved_at = timezone.now()
        self.order.save()
        self._complete_packing()
        DeliveryRecord.objects.create(order=self.order, status=DeliveryRecord.Status.SCHEDULED)
        response = self._update({"status": DeliveryRecord.Status.OUT})
        self.assertEqual(response.status_code, 200, response.content)

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

    def test_dispatch_is_blocked_until_packing_is_recorded(self):
        self.order.status = SalesOrder.Status.READY
        self.order.save(update_fields=["status", "updated_at"])
        DeliveryRecord.objects.create(order=self.order, status=DeliveryRecord.Status.SCHEDULED)
        response = self._update({"status": DeliveryRecord.Status.OUT})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Packing must be completed", response.json()["detail"])
        self.assertEqual(DeliveryRecord.objects.get(order=self.order).status, DeliveryRecord.Status.SCHEDULED)
