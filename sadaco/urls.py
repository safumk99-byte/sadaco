from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse
from django.urls import include, path, re_path
from django.views.static import serve
from accounts.push_views import service_worker


def react_app(request):
    return FileResponse(open(settings.BASE_DIR / "frontend" / "dist" / "index.html", "rb"), content_type="text/html")

urlpatterns = [
    path("service-worker.js", service_worker, name="service_worker"),
    re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "frontend" / "dist" / "assets"}),
    path("api/", include("core.api_urls")),
    path("api/sales/", include("sales.api_urls")),
    path("api/production/", include("production.api_urls")),
    path("api/quality/", include("quality.api_urls")),
    path("api/purchase/", include("purchase.api_urls")),
    path("api/finance/", include("finance.api_urls")),
    path("api/delivery/", include("delivery.api_urls")),
    path("api/marketing/", include("marketing.api_urls")),
    path("api/reports/", include("reports.api_urls")),
    re_path(r"^(?!api(?:/|$)|service-worker\.js$).*$", react_app, name="react_app"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
