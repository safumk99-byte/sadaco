import json
import logging
import os

from django.conf import settings

from .models import PushSubscription

logger = logging.getLogger(__name__)


def _vapid_private_key():
    return getattr(settings, "WEB_PUSH_PRIVATE_KEY", "")


def _vapid_claims():
    subject = getattr(settings, "WEB_PUSH_SUBJECT", "mailto:admin@sadaco.local").strip()
    return {"sub": subject}


def send_web_push(user, title, message="", url="", priority="normal"):
    """Send a best-effort Web Push notification to all active subscriptions for a user."""
    private_key = _vapid_private_key()
    if not private_key or not getattr(settings, "WEB_PUSH_ENABLED", False):
        return 0

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush is not installed; Web Push is disabled.")
        return 0

    subscriptions = list(PushSubscription.objects.filter(user=user, is_active=True))
    sent = 0
    payload = json.dumps({
        "title": title,
        "body": message,
        "url": url or "/",
        "priority": priority,
    })

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.as_webpush_info(),
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=_vapid_claims(),
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                subscription.is_active = False
                subscription.save(update_fields=["is_active", "updated_at"])
            logger.warning("Web Push failed for subscription %s: %s", subscription.pk, exc)
        except Exception as exc:
            logger.warning("Web Push failed for subscription %s: %s", subscription.pk, exc)
    return sent
