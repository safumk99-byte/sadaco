def customer_portal_notifications(request):
    """Expose customer-portal notification data without changing existing account notifications."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "customer_notification_count": 0,
            "customer_recent_notifications": [],
        }
    try:
        qs = request.user.customer_notifications.all()
    except Exception:
        return {
            "customer_notification_count": 0,
            "customer_recent_notifications": [],
        }
    return {
        "customer_notification_count": qs.filter(is_read=False).count(),
        "customer_recent_notifications": qs[:6],
    }
