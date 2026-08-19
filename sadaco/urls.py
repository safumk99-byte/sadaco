from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("staff/", include("staff.urls")),
    path("products/", include("products.urls")),
    path("reports/", include("reports.urls")),
    path("sales/", include("sales.urls")),
    path("production/", include("production.urls")),
    path("quality/", include("quality.urls")),
    path("inventory/", include("inventory.urls")),
    path("purchase/", include("purchase.urls")),
    path("finance/", include("finance.urls")),
    path("delivery/", include("delivery.urls")),
    path("marketing/", include("marketing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
