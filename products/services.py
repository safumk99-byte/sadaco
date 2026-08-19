from django.db.models import Q, F

from .models import Product, ProductCategory


def can_manage_products(user):
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_active and profile.role in {
        "super_admin", "institution_admin", "manager"
    })


def product_queryset():
    return Product.objects.select_related("category")


def dashboard_stats():
    return {
        "total_products": Product.objects.count(),
        "active_products": Product.objects.filter(status=Product.Status.ACTIVE).count(),
        "categories": ProductCategory.objects.count(),
        "low_stock": Product.objects.filter(
            status=Product.Status.ACTIVE,
            stock_quantity__lte=F("low_stock_threshold"),
        ).count(),
    }


def search_products(query=""):
    qs = product_queryset()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
        )
    return qs
