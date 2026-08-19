from django.contrib.auth.models import User
from django.db.models import Q

from .models import Notification, UserProfile


MANAGER_ROLES = {
    UserProfile.Role.SUPER_ADMIN,
    UserProfile.Role.INSTITUTION_ADMIN,
    UserProfile.Role.MANAGER,
}


def notify_roles(
    title,
    message="",
    notification_type=Notification.Type.INFO,
    priority=Notification.Priority.NORMAL,
    url="",
    roles=None,
    exclude_user=None,
):
    """Create an in-app notification for active managers/admins and superusers."""
    roles = roles or MANAGER_ROLES

    users = User.objects.filter(is_active=True).filter(
        Q(is_superuser=True) |
        Q(profile__is_active=True, profile__role__in=roles)
    ).distinct()

    if exclude_user and getattr(exclude_user, "is_authenticated", False):
        users = users.exclude(pk=exclude_user.pk)

    notifications = [
        Notification(
            user=user,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            url=url,
        )
        for user in users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)


def notify_user(
    user,
    title,
    message="",
    notification_type=Notification.Type.INFO,
    priority=Notification.Priority.NORMAL,
    url="",
):
    if not user or not user.is_active:
        return None
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        url=url,
    )
