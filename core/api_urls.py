from django.urls import path
from .api import (
    csrf, me, api_login, api_logout, dashboard_api,
    notifications_api, notification_read_api, notifications_read_all_api,
    push_config_api, push_subscribe_api, push_unsubscribe_api,
    users_api, user_create_api, user_update_api, profile_update_api,
    approvals_api, approval_review_api, audit_api, customer_requests_api,
    customer_request_update_api, staff_api, staff_detail_api, staff_options_api,
    staff_create_api, staff_update_api, staff_tasks_api, staff_task_status_api,
    staff_task_create_api, staff_attendance_api, staff_attendance_create_api,
    staff_performance_api, staff_performance_create_api, products_api,
    product_detail_api, product_create_api, product_update_api,
    product_categories_api, product_category_create_api, stock_transaction_api,
    stock_transactions_api,
)

urlpatterns = [
    path("auth/csrf/", csrf), path("auth/me/", me), path("auth/login/", api_login), path("auth/logout/", api_logout),
    path("dashboard/", dashboard_api), path("notifications/", notifications_api),
    path("notifications/<int:notification_id>/read/", notification_read_api), path("notifications/read-all/", notifications_read_all_api),
    path("push/config/", push_config_api), path("push/subscribe/", push_subscribe_api), path("push/unsubscribe/", push_unsubscribe_api),
    path("users/", users_api), path("users/create/", user_create_api), path("users/<int:pk>/update/", user_update_api), path("profile/", profile_update_api),
    path("approvals/", approvals_api), path("approvals/<int:pk>/review/", approval_review_api), path("audit-log/", audit_api),
    path("customer-requests/", customer_requests_api), path("customer-requests/<int:pk>/update/", customer_request_update_api),
    path("staff/", staff_api), path("staff/options/", staff_options_api), path("staff/<int:pk>/", staff_detail_api),
    path("staff/create/", staff_create_api), path("staff/<int:pk>/update/", staff_update_api), path("staff/tasks/", staff_tasks_api),
    path("staff/tasks/<int:pk>/status/", staff_task_status_api), path("staff/tasks/create/", staff_task_create_api),
    path("staff/attendance/", staff_attendance_api), path("staff/attendance/create/", staff_attendance_create_api),
    path("staff/performance/", staff_performance_api), path("staff/performance/create/", staff_performance_create_api),
    path("products/", products_api), path("products/categories/", product_categories_api), path("products/categories/create/", product_category_create_api),
    path("products/<int:pk>/", product_detail_api), path("products/create/", product_create_api), path("products/<int:pk>/update/", product_update_api),
    path("products/stock/", stock_transactions_api), path("products/stock/transaction/", stock_transaction_api),
]
