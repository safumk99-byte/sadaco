import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from core.models import Department
from products.models import ProductCategory
from staff.models import Designation, StaffProfile, WorkArea

from .models import Customer, CustomerFeedback, CustomerNotification, DeliveryRecord, DesignApproval, Enquiry, OrderRequest, PaymentRecord, Quotation, QuotationApproval, QuotationConfiguration, QuotationLineItem, SalesOrder


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


class SalesDepartmentAccessTests(TestCase):
    def setUp(self):
        from .api import _customer_qs, _enquiry_qs, _quotation_qs, _order_qs
        self.customer_qs = _customer_qs
        self.enquiry_qs = _enquiry_qs
        self.quotation_qs = _quotation_qs
        self.order_qs = _order_qs
        self.creatives = Department.objects.create(code="sales-creatives", name="Sales Creatives")
        self.cnc = Department.objects.create(code="sales-cnc", name="Sales CNC")
        self.manager = User.objects.create_user(username="sales_creatives_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.creatives)
        self.other_manager = User.objects.create_user(username="sales_cnc_mgr", password="StrongPass123!")
        UserProfile.objects.create(user=self.other_manager, role=UserProfile.Role.MANAGER, department=self.cnc)
        self.creative_customer = Customer.objects.create(
            name="Creative Customer", phone="9000000001", department=self.creatives
        )
        self.cnc_customer = Customer.objects.create(
            name="CNC Customer", phone="9000000002", department=self.cnc
        )
        self.creative_enquiry = Enquiry.objects.create(
            customer=self.creative_customer, channel=Enquiry.Channel.PHONE,
            product_type="Creative item", quantity=1, created_by=self.manager
        )
        self.cnc_enquiry = Enquiry.objects.create(
            customer=self.cnc_customer, channel=Enquiry.Channel.PHONE,
            product_type="CNC item", quantity=1, created_by=self.other_manager
        )
        self.creative_quotation = Quotation.objects.create(
            customer=self.creative_customer, item_description="Creative item",
            quantity=1, quoted_price=1000, created_by=self.manager
        )
        self.cnc_quotation = Quotation.objects.create(
            customer=self.cnc_customer, item_description="CNC item",
            quantity=1, quoted_price=2000, created_by=self.other_manager
        )
        self.creative_order = SalesOrder.objects.create(
            customer=self.creative_customer, item_description="Creative item",
            quantity=1, confirmed_price=1000, created_by=self.manager
        )
        self.cnc_order = SalesOrder.objects.create(
            customer=self.cnc_customer, item_description="CNC item",
            quantity=1, confirmed_price=2000, created_by=self.other_manager
        )

    def test_manager_sees_only_department_customers(self):
        self.assertEqual(
            set(self.customer_qs(self.manager).values_list("id", flat=True)),
            {self.creative_customer.id},
        )

    def test_manager_sees_only_department_enquiries_quotations_and_orders(self):
        self.assertEqual(
            set(self.enquiry_qs(self.manager).values_list("id", flat=True)),
            {self.creative_enquiry.id},
        )
        self.assertEqual(
            set(self.quotation_qs(self.manager).values_list("id", flat=True)),
            {self.creative_quotation.id},
        )
        self.assertEqual(
            set(self.order_qs(self.manager).values_list("id", flat=True)),
            {self.creative_order.id},
        )

    def test_unassigned_manager_has_no_sales_data(self):
        user = User.objects.create_user(username="sales_unassigned", password="StrongPass123!")
        UserProfile.objects.create(user=user, role=UserProfile.Role.MANAGER)
        self.assertFalse(self.customer_qs(user).exists())
        self.assertFalse(self.enquiry_qs(user).exists())
        self.assertFalse(self.quotation_qs(user).exists())
        self.assertFalse(self.order_qs(user).exists())

    def test_global_admin_sees_all_sales_departments(self):
        admin = User.objects.create_superuser(username="sales_root", password="StrongPass123!")
        self.assertEqual(self.customer_qs(admin).count(), 2)
        self.assertEqual(self.enquiry_qs(admin).count(), 2)
        self.assertEqual(self.quotation_qs(admin).count(), 2)
        self.assertEqual(self.order_qs(admin).count(), 2)


class SalesOrderLifecyclePermissionTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="sales-lifecycle", name="Sales Lifecycle")
        self.manager = User.objects.create_user(username="sales_lifecycle_mgr", password="StrongPass123!")
        UserProfile.objects.create(
            user=self.manager,
            role=UserProfile.Role.MANAGER,
            department=self.department,
        )
        self.customer = Customer.objects.create(
            name="Lifecycle Customer",
            phone="9000000088",
            department=self.department,
        )

    def _payload(self, status, notes=""):
        return {
            "customer": self.customer.pk,
            "quotation": "",
            "item_description": "Lifecycle Item",
            "quantity": "1",
            "confirmed_price": "1000",
            "design_reference": "",
            "delivery_date": "",
            "deadline": "",
            "responsible_staff": "",
            "advance_required": "0",
            "status": status,
            "notes": notes,
        }

    def test_sales_cannot_create_order_as_delivered(self):
        from django.test import RequestFactory
        from .api import order_create
        request = RequestFactory().post(
            "/api/sales/orders/create/",
            data=json.dumps(self._payload(SalesOrder.Status.DELIVERED)),
            content_type="application/json",
        )
        request.user = self.manager
        response = order_create(request)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SalesOrder.objects.filter(customer=self.customer).exists())

    def test_sales_cannot_move_confirmed_order_directly_to_ready(self):
        from django.test import RequestFactory
        from .api import order_update
        order = SalesOrder.objects.create(
            customer=self.customer,
            item_description="Lifecycle Item",
            quantity=1,
            confirmed_price=1000,
            status=SalesOrder.Status.CONFIRMED,
        )
        request = RequestFactory().post(
            f"/api/sales/orders/{order.pk}/update/",
            data=json.dumps(self._payload(SalesOrder.Status.READY)),
            content_type="application/json",
        )
        request.user = self.manager
        response = order_update(request, order.pk)
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CONFIRMED)

    def test_sales_cannot_rewind_delivered_order_to_confirmed(self):
        from django.test import RequestFactory
        from .api import order_update
        order = SalesOrder.objects.create(
            customer=self.customer,
            item_description="Delivered Item",
            quantity=1,
            confirmed_price=1000,
            status=SalesOrder.Status.DELIVERED,
        )
        request = RequestFactory().post(
            f"/api/sales/orders/{order.pk}/update/",
            data=json.dumps(self._payload(SalesOrder.Status.CONFIRMED, notes="Edited notes")),
            content_type="application/json",
        )
        request.user = self.manager
        response = order_update(request, order.pk)
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.DELIVERED)

    def test_sales_can_edit_non_lifecycle_fields_without_changing_delivered_status(self):
        from django.test import RequestFactory
        from .api import order_update
        order = SalesOrder.objects.create(
            customer=self.customer,
            item_description="Delivered Item",
            quantity=1,
            confirmed_price=1000,
            status=SalesOrder.Status.DELIVERED,
        )
        request = RequestFactory().post(
            f"/api/sales/orders/{order.pk}/update/",
            data=json.dumps(self._payload(SalesOrder.Status.DELIVERED, notes="Updated note")),
            content_type="application/json",
        )
        request.user = self.manager
        response = order_update(request, order.pk)
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.DELIVERED)
        self.assertEqual(order.notes, "Updated note")


class CustomerMasterRequirementsTests(TestCase):
    def test_customer_number_is_generated_and_stable(self):
        customer = Customer.objects.create(
            name="Unique Customer", phone="+91 98765 43210", customer_type="Retail"
        )
        first_number = customer.customer_no
        self.assertTrue(first_number.startswith("CUS-"))
        customer.name = "Updated Customer"
        customer.save()
        self.assertEqual(customer.customer_no, first_number)
        self.assertEqual(customer.customer_type, "Retail")

    def test_customer_form_rejects_duplicate_mobile_with_different_formatting(self):
        from .forms import CustomerForm
        Customer.objects.create(name="Existing", phone="+91 98765-43210")
        form = CustomerForm(data={
            "name": "Duplicate", "customer_type": "Retail", "phone": "919876543210",
            "alternate_phone": "", "email": "", "address": "", "status": "active", "notes": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_customer_form_allows_same_customer_to_keep_its_mobile(self):
        from .forms import CustomerForm
        customer = Customer.objects.create(name="Existing", phone="+91 98765-43210")
        form = CustomerForm(data={
            "name": "Existing Updated", "customer_type": "Business", "phone": "+91 98765-43210",
            "alternate_phone": "", "email": "", "address": "", "status": "active", "notes": "",
        }, instance=customer)
        self.assertTrue(form.is_valid(), form.errors)


class CustomerInteractionApiTests(TestCase):
    def setUp(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()
        self.department = Department.objects.create(code="crm-followup", name="CRM Follow-up")
        self.manager = User.objects.create_user(username="crm_manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.customer = Customer.objects.create(name="CRM Customer", phone="9000001234", department=self.department)

    def test_manager_can_create_and_view_customer_interaction(self):
        from .api import customer_interactions, customer_interaction_complete
        payload = {
            "interaction_type": "call", "subject": "Discussed quotation",
            "notes": "Customer requested a revised estimate.",
            "next_follow_up": date.today().isoformat(), "completed": False,
        }
        request = self.factory.post(
            f"/api/sales/customers/{self.customer.pk}/interactions/",
            data=json.dumps(payload), content_type="application/json",
        )
        request.user = self.manager
        created = customer_interactions(request, self.customer.pk)
        self.assertEqual(created.status_code, 201)
        request = self.factory.get(f"/api/sales/customers/{self.customer.pk}/interactions/")
        request.user = self.manager
        response = customer_interactions(request, self.customer.pk)
        self.assertEqual(response.status_code, 200)
        record = response.json()["interactions"][0]
        self.assertEqual(record["subject"], "Discussed quotation")
        self.assertFalse(record["completed"])
        self.assertFalse(record["overdue"])
        interaction_id = record["id"]
        complete_request = self.factory.post(f"/api/sales/customers/{self.customer.pk}/interactions/{interaction_id}/complete/")
        complete_request.user = self.manager
        completed = customer_interaction_complete(complete_request, self.customer.pk, interaction_id)
        self.assertEqual(completed.status_code, 200)
        self.assertTrue(completed.json()["completed"])

    def test_manager_cannot_access_another_department_customer_history(self):
        from .api import customer_interactions
        other_department = Department.objects.create(code="crm-other", name="CRM Other")
        other_customer = Customer.objects.create(name="Other CRM Customer", phone="9000001235", department=other_department)
        request = self.factory.get(f"/api/sales/customers/{other_customer.pk}/interactions/")
        request.user = self.manager
        response = customer_interactions(request, other_customer.pk)
        self.assertEqual(response.status_code, 404)

    def test_non_manager_cannot_create_customer_interaction(self):
        from .api import customer_interactions
        staff_user = User.objects.create_user(username="crm_staff", password="StrongPass123!")
        UserProfile.objects.create(user=staff_user, role=UserProfile.Role.STAFF, department=self.department)
        request = self.factory.post(
            f"/api/sales/customers/{self.customer.pk}/interactions/",
            data=json.dumps({"interaction_type": "call", "subject": "Unauthorized"}),
            content_type="application/json",
        )
        request.user = staff_user
        with self.assertRaises(Exception):
            customer_interactions(request, self.customer.pk)



class QuotationWorkflowApiTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Creatives", code="CRE")
        self.manager = User.objects.create_user(username="quote_manager", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role=UserProfile.Role.MANAGER, department=self.department)
        self.founder = User.objects.create_user(username="quote_founder", password="StrongPass123!")
        UserProfile.objects.create(user=self.founder, role=UserProfile.Role.SUPER_ADMIN)
        self.customer = Customer.objects.create(
            name="Quotation Customer", phone="9876543210", department=self.department,
        )
        self.config = QuotationConfiguration.objects.create(
            company_name="SADACO GROUP OF COMPANIES",
            tax_label="Tax",
            tax_rate=Decimal("5.00"),
            manager_discount_limit_percent=Decimal("10.00"),
            default_terms="Payment terms as agreed.",
        )

    def _create_quotation(self, discount="15"):
        self.client.login(username="quote_manager", password="StrongPass123!")
        response = self.client.post(
            "/api/sales/quotations/create-workflow/",
            data=json.dumps({
                "customer": self.customer.pk,
                "item_description": "Custom Acrylic Award",
                "dimensions": "12 x 8 inch",
                "quantity": "1",
                "discount_percent": discount,
                "valid_until": "2026-12-31",
                "line_items": [{
                    "category": "material",
                    "description": "Acrylic sheet and base",
                    "dimensions": "12 x 8 inch",
                    "quantity": "2",
                    "unit": "piece",
                    "unit_price": "500",
                }],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["quotation"]

    def test_discount_above_manager_limit_requires_founder_approval(self):
        quotation_data = self._create_quotation("15")
        quotation_id = quotation_data["id"]
        self.assertEqual(quotation_data["subtotal"], "1000.00")
        self.assertEqual(quotation_data["quoted_price"], "1050.00")

        response = self.client.post(
            f"/api/sales/quotations/{quotation_id}/submit/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["quotation"]["status"], Quotation.Status.PENDING_APPROVAL)
        self.assertEqual(QuotationApproval.objects.filter(quotation_id=quotation_id, action=QuotationApproval.Action.REQUESTED).count(), 1)

        denied = self.client.post(
            f"/api/sales/quotations/{quotation_id}/approval/",
            data=json.dumps({"action": "approve"}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)

        self.client.logout()
        self.client.login(username="quote_founder", password="StrongPass123!")
        approved = self.client.post(
            f"/api/sales/quotations/{quotation_id}/approval/",
            data=json.dumps({"action": "approve", "notes": "Approved by Founder."}),
            content_type="application/json",
        )
        self.assertEqual(approved.status_code, 200, approved.content)
        result = approved.json()["quotation"]
        self.assertEqual(result["status"], Quotation.Status.SENT)
        self.assertEqual(result["discount_amount"], "150.00")
        self.assertEqual(result["tax_amount"], "42.50")
        self.assertEqual(result["quoted_price"], "892.50")
        self.assertEqual(QuotationApproval.objects.filter(quotation_id=quotation_id, action=QuotationApproval.Action.APPROVED).count(), 1)

        pdf = self.client.get(f"/api/sales/quotations/{quotation_id}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_discount_within_manager_limit_can_be_sent_without_approval(self):
        quotation_data = self._create_quotation("5")
        response = self.client.post(
            f"/api/sales/quotations/{quotation_data['id']}/submit/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["quotation"]["status"], Quotation.Status.SENT)
        self.assertEqual(response.json()["quotation"]["quoted_price"], "997.50")
        self.assertFalse(QuotationApproval.objects.filter(quotation_id=quotation_data["id"]).exists())

    def test_tax_must_be_configured_before_sending(self):
        self.config.tax_rate = None
        self.config.save()
        quotation_data = self._create_quotation("0")
        response = self.client.post(
            f"/api/sales/quotations/{quotation_data['id']}/submit/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("configure the tax rate", response.json()["detail"])

    def test_founder_only_can_change_quotation_configuration(self):
        self.client.login(username="quote_manager", password="StrongPass123!")
        denied = self.client.post(
            "/api/sales/quotations/configuration/",
            data=json.dumps({"tax_rate": "7.5"}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.client.logout()
        self.client.login(username="quote_founder", password="StrongPass123!")
        allowed = self.client.post(
            "/api/sales/quotations/configuration/",
            data=json.dumps({"tax_rate": "7.5", "manager_discount_limit_percent": "12"}),
            content_type="application/json",
        )
        self.assertEqual(allowed.status_code, 200, allowed.content)
        self.assertEqual(allowed.json()["configuration"]["tax_rate"], "7.5")
        self.assertEqual(allowed.json()["configuration"]["manager_discount_limit_percent"], "12")

    def test_customer_acceptance_uses_accepted_status(self):
        quotation_data = self._create_quotation("0")
        quotation_id = quotation_data["id"]
        self.client.post(
            f"/api/sales/quotations/{quotation_id}/submit/",
            data="{}",
            content_type="application/json",
        )
        customer_user = User.objects.create_user(username="quotation_customer", password="StrongPass123!")
        self.customer.user = customer_user
        self.customer.save(update_fields=["user"])
        self.client.logout()
        self.client.login(username="quotation_customer", password="StrongPass123!")
        response = self.client.post(
            f"/api/sales/portal/quotations/{quotation_id}/respond/",
            data=json.dumps({"decision": "accepted"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["quotation"]["status"], Quotation.Status.ACCEPTED)
        pdf = self.client.get(f"/api/sales/portal/quotations/{quotation_id}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
