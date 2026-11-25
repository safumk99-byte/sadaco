from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, DesignRevisionViewSet, EnquiryViewSet, FollowUpViewSet, health

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("enquiries", EnquiryViewSet, basename="enquiry")
router.register("follow-ups", FollowUpViewSet, basename="follow-up")
router.register("design-revisions", DesignRevisionViewSet, basename="design-revision")

urlpatterns = [
    path("health/", health, name="api-health"),
    path("", include(router.urls)),
]
