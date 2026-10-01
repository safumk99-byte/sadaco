import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .models import PushSubscription


def service_worker(request):
    js = """
self.addEventListener('push', function(event) {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) {}
  const title = data.title || 'SADACO';
  const options = {
    body: data.body || 'You have a new notification.',
    icon: '/static/images/sadaco-logo-white.png',
    badge: '/static/images/sadaco-logo-white.png',
    data: { url: data.url || '/' },
    tag: 'sadaco-notification',
    renotify: true,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const target = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
    for (const client of clientList) {
      if ('focus' in client) {
        client.navigate(target);
        return client.focus();
      }
    }
    if (clients.openWindow) return clients.openWindow(target);
  }));
});
"""
    return HttpResponse(js, content_type="application/javascript")


@login_required
@require_POST
def save_push_subscription(request):
    try:
        data = json.loads(request.body or "{}")
        endpoint = (data.get("endpoint") or "").strip()
        keys = data.get("keys") or {}
        p256dh = (keys.get("p256dh") or "").strip()
        auth = (keys.get("auth") or "").strip()
        if not endpoint or not p256dh or not auth:
            return JsonResponse({"ok": False, "error": "Invalid push subscription."}, status=400)

        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:4000],
                "is_active": True,
            },
        )
        return JsonResponse({"ok": True, "subscription_id": subscription.pk})
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)


@login_required
@require_POST
def remove_push_subscription(request):
    try:
        data = json.loads(request.body or "{}")
    except (ValueError, TypeError, json.JSONDecodeError):
        data = {}
    endpoint = (data.get("endpoint") or "").strip()
    if endpoint:
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).update(is_active=False)
    else:
        PushSubscription.objects.filter(user=request.user).update(is_active=False)
    return JsonResponse({"ok": True})
