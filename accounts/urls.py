from django.urls import path
from .views import (
    Login, logout_view, my_profile, user_create, user_edit, user_list,
    user_password, notifications, mark_notification_read,
    mark_all_notifications_read,
)
app_name = "accounts"
urlpatterns = [
    path("login/", Login.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", my_profile, name="my_profile"),
    path("users/", user_list, name="user_list"),
    path("users/create/", user_create, name="user_create"),
    path("users/<int:user_id>/edit/", user_edit, name="user_edit"),
    path("users/<int:user_id>/password/", user_password, name="user_password"),
    path("notifications/", notifications, name="notifications"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="notification_read"),
    path("notifications/read-all/", mark_all_notifications_read, name="notifications_read_all"),
]
