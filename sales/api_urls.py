from django.urls import path
from .api import *
from .portal_api import *
urlpatterns = [
    path("summary/", summary), path("customers/", customers), path("customers/create/", customer_create), path("customers/<int:pk>/update/", customer_update),
    path("enquiries/", enquiries), path("enquiries/create/", enquiry_create), path("enquiries/<int:pk>/update/", enquiry_update),
    path("quotations/", quotations), path("quotations/create/", quotation_create), path("quotations/<int:pk>/update/", quotation_update),
    path("orders/", orders), path("orders/create/", order_create), path("orders/<int:pk>/update/", order_update),
    path("portal/register/", portal_register), path("portal/summary/", portal_summary), path("portal/profile/", portal_profile),
    path("portal/products/", portal_products), path("portal/products/<int:pk>/", portal_product_detail),
    path("portal/notifications/", portal_notifications), path("portal/notifications/<int:pk>/read/", portal_notification_read),
    path("portal/requests/", portal_requests), path("portal/requests/create/", portal_request_create), path("portal/requests/<int:pk>/", portal_request_detail),
    path("portal/quotations/", portal_quotations), path("portal/quotations/<int:pk>/", portal_quotation_detail), path("portal/quotations/<int:pk>/respond/", portal_quotation_response),
    path("portal/designs/<int:pk>/respond/", portal_design_response), path("portal/orders/", portal_orders), path("portal/orders/<int:pk>/", portal_order_detail),
    path("portal/orders/<int:pk>/feedback/", portal_feedback),
]
