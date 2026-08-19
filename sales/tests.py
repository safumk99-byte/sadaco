from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from products.models import ProductCategory
from staff.models import Designation, StaffProfile, WorkArea

from .models import Customer, CustomerFeedback, CustomerNotification, DeliveryRecord, DesignApproval, Enquiry, OrderRequest, PaymentRecord, Quotation, SalesOrder


class SalesModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Test Customer", phone="9999999999")

    def test_document_numbers_are_generated(self):
        enquiry = Enquiry.objects.create(
            customer=self.customer, channel=Enquiry.Channel.PHONE,
            product_type="Memento", quantity=Decimal("2")
        )
        quotation = Quotation.objects.create(
            customer=self.customer, item_description="Memento", quantity=Decimal("2"),
            quoted_price=Decimal("1000")
        )
        order = SalesOrder.objects.create(
            customer=self.customer, item_description="Memento", quantity=Decimal("2"),
            confirmed_price=Decimal("1000")
        )
        self.assertTrue(enquiry.enquiry_no.startswith("ENQ-"))
        self.assertTrue(quotation.quotation_no.startswith("QUO-"))
        self.assertTrue(order.order_no.startswith("ORD-"))

    def test_quotation_cost_total(self):
        quotation = Quotation.objects.create(
            customer=self.customer, item_description="Trophy", quantity=1,
            material_cost=100, labour_cost=50, machine_cost=25,
            finishing_cost=10, packaging_cost=5, delivery_cost=10,
            quoted_price=300,
        )
        self.assertEqual(quotation.cost_total, Decimal("200"))


class SalesPermissionTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="salesstaff", password="StrongPass123!")
        UserProfile.objects.create(user=self.staff_user, role=UserProfile.Role.STAFF)
        self.manager = User.objects.create_user(username="salesmanager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)

    def test_staff_can_view_sales_dashboard(self):
        self.client.login(username="salesstaff", password="StrongPass123!")
        response = self.client.get(reverse("sales:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_create_customer(self):
        self.client.login(username="salesstaff", password="StrongPass123!")
        response = self.client.get(reverse("sales:customer_create"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_create_customer(self):
        self.client.login(username="salesmanager", password="StrongPass123!")
        response = self.client.post(reverse("sales:customer_create"), {
            "name": "New Customer", "phone": "8888888888", "alternate_phone": "",
            "email": "", "address": "", "status": "active", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(phone="8888888888").exists())


class SalesValidationTests(TestCase):
    def setUp(self):
        self.customer_a = Customer.objects.create(name="Customer A", phone="1111111111")
        self.customer_b = Customer.objects.create(name="Customer B", phone="2222222222")
        self.quotation = Quotation.objects.create(
            customer=self.customer_a, item_description="Wall Decor", quantity=1,
            quoted_price=Decimal("5000")
        )

    def test_quotation_customer_mismatch_is_rejected(self):
        from .forms import SalesOrderForm
        form = SalesOrderForm(data={
            "customer": self.customer_b.pk,
            "quotation": self.quotation.pk,
            "item_description": "Wall Decor",
            "quantity": "1",
            "confirmed_price": "5000",
            "design_reference": "",
            "delivery_date": "2026-08-25",
            "deadline": "2026-08-20",
            "responsible_staff": "",
            "advance_required": "1000",
            "status": "confirmed",
            "notes": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("quotation", form.errors)


class CustomerPortalTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="portalmanager", password="StrongPass123!"
        )
        UserProfile.objects.create(
            user=self.manager, role=UserProfile.Role.MANAGER
        )
        self.customer_user = User.objects.create_user(
            username="c_9999999999", password="StrongPass123!"
        )
        self.customer = Customer.objects.create(
            user=self.customer_user, name="Portal Customer", phone="9999999999"
        )

    def test_customer_portal_requires_customer_link(self):
        self.client.login(username="portalmanager", password="StrongPass123!")
        response = self.client.get(reverse("sales:portal_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_customer_can_submit_request_and_manager_is_notified(self):
        self.client.login(username="c_9999999999", password="StrongPass123!")
        response = self.client.post(
            reverse("sales:portal_request_create"),
            {
                "request_type": "order_request",
                "product": "",
                "product_name": "Custom Wall Decor",
                "quantity": "2",
                "size": "4x2 ft",
                "material_preference": "Wood",
                "requirement": "Custom carved design",
                "budget": "50000",
                "requested_date": "2026-09-01",
                "design_requirement": "Use reference image",
            },
        )
        self.assertEqual(response.status_code, 302)
        request_obj = OrderRequest.objects.get(customer=self.customer)
        self.assertEqual(request_obj.status, OrderRequest.Status.NEW)
        self.assertTrue(
            CustomerNotification.objects.filter(
                user=self.manager,
                notification_type=CustomerNotification.NotificationType.REQUEST,
                message__contains=request_obj.request_no,
            ).exists()
        )

    def test_customer_cannot_view_another_customers_request(self):
        other_user = User.objects.create_user(
            username="c_8888888888", password="StrongPass123!"
        )
        other = Customer.objects.create(
            user=other_user, name="Other Customer", phone="8888888888"
        )
        request_obj = OrderRequest.objects.create(
            customer=other,
            product_name="Private Request",
            quantity=1,
            requirement="Private",
        )
        self.client.login(username="c_9999999999", password="StrongPass123!")
        response = self.client.get(
            reverse("sales:portal_request_detail", kwargs={"pk": request_obj.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_manager_can_review_request_and_customer_gets_status_notification(self):
        request_obj = OrderRequest.objects.create(
            customer=self.customer,
            product_name="Custom Product",
            quantity=1,
            requirement="Requirement",
        )
        self.client.login(username="portalmanager", password="StrongPass123!")
        response = self.client.post(
            reverse("sales:manager_request_review", kwargs={"pk": request_obj.pk}),
            {"status": "contacted", "manager_notes": "Manager will call customer."},
        )
        self.assertEqual(response.status_code, 302)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, OrderRequest.Status.CONTACTED)
        self.assertTrue(
            CustomerNotification.objects.filter(
                user=self.customer_user,
                notification_type=CustomerNotification.NotificationType.STATUS,
            ).exists()
        )


class CustomerSalesWorkflowTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="workflowmanager", password="StrongPass123!"
        )
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER)
        self.customer_user = User.objects.create_user(
            username="workflowcustomer", password="StrongPass123!"
        )
        self.customer = Customer.objects.create(
            user=self.customer_user, name="Workflow Customer", phone="7777777777"
        )
        self.quotation = Quotation.objects.create(
            customer=self.customer,
            item_description="Custom Memento",
            quantity=2,
            quoted_price=Decimal("5000"),
            advance_required=Decimal("2000"),
            status=Quotation.Status.SENT,
        )

    def test_customer_can_accept_quotation_and_manager_is_notified(self):
        self.client.login(username="workflowcustomer", password="StrongPass123!")
        response = self.client.post(
            reverse("sales:portal_quotation_response", kwargs={"pk": self.quotation.pk}),
            {"decision": "approved"},
        )
        self.assertEqual(response.status_code, 302)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, Quotation.Status.APPROVED)
        self.assertTrue(
            CustomerNotification.objects.filter(
                user=self.manager,
                notification_type=CustomerNotification.NotificationType.QUOTATION,
            ).exists()
        )

    def test_manager_can_confirm_only_approved_quotation(self):
        self.client.login(username="workflowmanager", password="StrongPass123!")
        response = self.client.post(
            reverse("sales:confirm_quotation_order", kwargs={"pk": self.quotation.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SalesOrder.objects.filter(quotation=self.quotation).count(), 0)

        self.quotation.status = Quotation.Status.APPROVED
        self.quotation.save(update_fields=["status", "updated_at"])
        response = self.client.post(
            reverse("sales:confirm_quotation_order", kwargs={"pk": self.quotation.pk})
        )
        self.assertEqual(response.status_code, 302)
        order = SalesOrder.objects.get(quotation=self.quotation)
        self.assertEqual(order.customer_id, self.customer.pk)
        self.assertTrue(DeliveryRecord.objects.filter(order=order).exists())
        self.assertTrue(
            CustomerNotification.objects.filter(
                user=self.customer_user,
                notification_type=CustomerNotification.NotificationType.ORDER,
            ).exists()
        )

    def test_design_approval_blocks_order_until_approved(self):
        self.quotation.status = Quotation.Status.APPROVED
        self.quotation.save(update_fields=["status", "updated_at"])
        DesignApproval.objects.create(
            quotation=self.quotation, version=1, status=DesignApproval.Status.SENT
        )
        self.client.login(username="workflowmanager", password="StrongPass123!")
        response = self.client.post(
            reverse("sales:confirm_quotation_order", kwargs={"pk": self.quotation.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SalesOrder.objects.filter(quotation=self.quotation).count(), 0)

    def test_feedback_requires_delivered_order(self):
        order = SalesOrder.objects.create(
            customer=self.customer, item_description="Delivered Item",
            quantity=1, confirmed_price=1000, status=SalesOrder.Status.DELIVERED
        )
        self.client.login(username="workflowcustomer", password="StrongPass123!")
        response = self.client.post(
            reverse("sales:portal_feedback", kwargs={"pk": order.pk}),
            {"rating": "5", "comment": "Excellent"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomerFeedback.objects.filter(order=order, rating=5).exists())
