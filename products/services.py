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
    # Product Management contains internal materials only. Customer catalogue
    # products are managed through the separate Catalogue workflow.
    return Product.objects.select_related("category").filter(customer_visible=False)


def dashboard_stats():
    internal = Product.objects.filter(customer_visible=False)
    return {
        "total_products": internal.count(),
        "active_products": internal.filter(status=Product.Status.ACTIVE).count(),
        "categories": ProductCategory.objects.filter(parent__isnull=True, is_section=False).count(),
        "low_stock": internal.filter(
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
