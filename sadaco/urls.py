from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from accounts.push_views import service_worker

urlpatterns = [
    path("service-worker.js", service_worker, name="service_worker"),
    path("api/", include("core.api_urls")),
    path("api/sales/", include("sales.api_urls")),
    path("api/production/", include("production.api_urls")),
    path("api/quality/", include("quality.api_urls")),
    path("api/purchase/", include("purchase.api_urls")),
    path("api/finance/", include("finance.api_urls")),
    path("api/delivery/", include("delivery.api_urls")),
    path("api/marketing/", include("marketing.api_urls")),
    path("api/reports/", include("reports.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
