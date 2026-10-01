def notifications(request):
    if not request.user.is_authenticated:
        return {"notification_count": 0, "recent_notifications": []}
    qs = request.user.notifications.all()
    return {
        "notification_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:5],
    }


def web_push(request):
    from django.conf import settings
    return {"WEB_PUSH_PUBLIC_KEY": getattr(settings, "WEB_PUSH_PUBLIC_KEY", "")}
