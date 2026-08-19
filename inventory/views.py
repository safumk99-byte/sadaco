from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Notification, UserProfile
from products.models import Product, StockTransaction
from production.models import ProductionJob, ProductionMaterial
from .forms import MaterialIssueForm, StockCountForm, ReorderLevelForm
from .models import MaterialIssue, ReorderAlert, StockCount
from .services import complete_stock_count, issue_material, sync_reorder_alerts

manager_required = role_required("super_admin", "institution_admin", "manager")


def _manager(user):
    return user.is_superuser or getattr(getattr(user, "profile", None), "role", None) in (
        "super_admin", "institution_admin", "manager"
    )


@login_required
@manager_required
def dashboard(request):
    sync_reorder_alerts()
    products = Product.objects.filter(status=Product.Status.ACTIVE)
    recent = StockTransaction.objects.select_related("product", "created_by")[:30]
    issues = MaterialIssue.objects.select_related("job", "material", "issued_by")[:20]
    context = {
        "title": "Inventory & Materials",
        "products": products,
        "recent": recent,
        "issues": issues,
        "low_stock": products.filter(stock_quantity__lte=F("low_stock_threshold")).count(),
        "out_of_stock": products.filter(stock_quantity=0).count(),
        "total_value": sum((p.stock_quantity * p.cost_price for p in products), 0),
        "issued_total": MaterialIssue.objects.filter(status=MaterialIssue.Status.ISSUED).aggregate(
            total=Sum("quantity")
        )["total"] or 0,
        "reorders": ReorderAlert.objects.filter(is_open=True).count(),
    }
    return render(request, "inventory/dashboard.html", context)


@login_required
@manager_required
def issue_create(request, material_id):
    material = get_object_or_404(
        ProductionMaterial.objects.select_related("job", "product"),
        pk=material_id,
    )
    if not material.product_id:
        messages.error(request, "This material is not linked to a stock product.")
        return redirect("production:job_detail", pk=material.job_id)

    pending = material.pending_quantity
    form = MaterialIssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            issue_material(
                material_id=material.pk,
                quantity=form.cleaned_data["quantity"],
                user=request.user,
                reference=form.cleaned_data["reference"],
                remarks=form.cleaned_data["remarks"],
            )
        except Exception as exc:
            form.add_error(None, str(exc))
        else:
            for profile in UserProfile.objects.filter(
                role__in=[
                    UserProfile.Role.SUPER_ADMIN,
                    UserProfile.Role.INSTITUTION_ADMIN,
                    UserProfile.Role.MANAGER,
                ],
                is_active=True,
            ):
                Notification.objects.create(
                    user=profile.user,
                    notification_type=Notification.Type.STOCK,
                    priority=Notification.Priority.NORMAL,
                    title="Material issued",
                    message=f"{material.product.name} issued to {material.job.job_no}.",
                    url=f"/production/jobs/{material.job_id}/",
                )
            messages.success(request, "Material issued to production successfully.")
            return redirect("production:job_detail", pk=material.job_id)

    return render(request, "inventory/issue_form.html", {
        "title": "Issue Material",
        "form": form,
        "material": material,
        "pending": pending,
    })


@login_required
@manager_required
def stock_count_create(request):
    form = StockCountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            variance = complete_stock_count(
                product_id=form.cleaned_data["product"].pk,
                counted_quantity=form.cleaned_data["counted_quantity"],
                user=request.user,
                reason=form.cleaned_data["reason"],
            )
        except Exception as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"Stock count completed. Variance: {variance}.")
            return redirect("inventory:dashboard")
    return render(request, "inventory/stock_count_form.html", {
        "title": "Physical Stock Count", "form": form
    })


@login_required
@manager_required
def reorder_list(request):
    alerts = sync_reorder_alerts()
    open_alerts = ReorderAlert.objects.filter(
        is_open=True
    ).select_related("product", "product__category")
    return render(request, "inventory/reorder.html", {
        "title": "Reorder Alerts",
        "alerts": open_alerts,
        "products": Product.objects.filter(status=Product.Status.ACTIVE),
    })
