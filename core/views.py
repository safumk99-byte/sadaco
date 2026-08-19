from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.decorators import role_required
from .forms import ApprovalRequestForm, ApprovalReviewForm
from .models import ApprovalRequest, AuditLog
from accounts.models import UserProfile, Notification
from django.utils import timezone

from products.models import Product, StockTransaction
from staff.models import StaffAttendance, StaffProfile, StaffTask
from sales.models import Customer, Enquiry, SalesOrder, OrderRequest, PaymentRecord


@login_required
def dashboard(request):
    if hasattr(request.user, "customer_profile"):
        return redirect("sales:portal_dashboard")

    today = timezone.localdate()

    # Core operational KPIs.
    total_staff = StaffProfile.objects.count()
    active_staff = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).count()
    present_today = StaffAttendance.objects.filter(
        date=today, status=StaffAttendance.Status.PRESENT
    ).count()

    stats = {
        "total_staff": total_staff,
        "active_staff": active_staff,
        "total_products": Product.objects.count(),
        "low_stock": Product.objects.filter(
            status=Product.Status.ACTIVE,
            stock_quantity__lte=F("low_stock_threshold"),
        ).count(),
        "open_tasks": StaffTask.objects.exclude(
            status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
        ).count(),
        "present_today": present_today,
        "attendance_rate": round((present_today / active_staff) * 100) if active_staff else 0,
        "customers": Customer.objects.filter(status=Customer.Status.ACTIVE).count(),
        "new_enquiries": Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
        "pending_requests": OrderRequest.objects.filter(
            status__in=[
                OrderRequest.Status.NEW,
                OrderRequest.Status.REVIEWING,
                OrderRequest.Status.CONTACTED,
                OrderRequest.Status.QUOTATION,
            ]
        ).count(),
        "active_orders": SalesOrder.objects.exclude(
            status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]
        ).count(),
        "overdue_tasks": StaffTask.objects.filter(
            due_date__lt=today
        ).exclude(
            status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
        ).count(),
    }

    recent_tasks = StaffTask.objects.select_related(
        "assigned_to__user"
    ).order_by("-created_at")[:6]

    recent_stock = StockTransaction.objects.select_related(
        "product", "created_by"
    ).order_by("-created_at")[:6]

    recent_orders = SalesOrder.objects.select_related(
        "customer"
    ).order_by("-created_at")[:6]

    recent_enquiries = Enquiry.objects.select_related(
        "customer"
    ).order_by("-created_at")[:5]

    low_stock_products = Product.objects.filter(
        status=Product.Status.ACTIVE,
        stock_quantity__lte=F("low_stock_threshold"),
    ).order_by("stock_quantity", "name")[:6]

    profile = getattr(request.user, "profile", None)
    role = "super_admin" if request.user.is_superuser else getattr(profile, "role", "staff")

    return render(request, "core/dashboard.html", {
        "title": "SADACO Dashboard",
        "stats": stats,
        "recent_tasks": recent_tasks,
        "recent_stock": recent_stock,
        "recent_orders": recent_orders,
        "recent_enquiries": recent_enquiries,
        "low_stock_products": low_stock_products,
        "today": today,
        "is_manager": role in {"super_admin", "institution_admin", "manager"},
        "is_super_admin": role == "super_admin",
        "is_institution_admin": role == "institution_admin",
        "is_staff_user": role == "staff",
        "user_role": role,
    })


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse(
            {"status": "error", "database": "error"},
            status=503,
        )

    return JsonResponse({"status": "ok", "database": "ok"})


@login_required
@role_required("super_admin", "institution_admin", "manager")
def approval_list(request):
    status = request.GET.get("status", "").strip()
    qs = ApprovalRequest.objects.select_related("requested_by", "reviewed_by")
    if status:
        qs = qs.filter(status=status)
    return render(request, "core/approvals.html", {
        "title": "Approval Center",
        "requests": qs,
        "selected_status": status,
        "status_choices": ApprovalRequest.Status.choices,
    })


@login_required
@role_required("super_admin", "institution_admin", "manager")
def approval_create(request):
    form = ApprovalRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.requested_by = request.user
        item.save()
        manager_users = User.objects.filter(
            profile__role__in=[
                UserProfile.Role.SUPER_ADMIN,
                UserProfile.Role.INSTITUTION_ADMIN,
                UserProfile.Role.MANAGER,
            ],
            profile__is_active=True,
            is_active=True,
        ).exclude(pk=request.user.pk).distinct()
        for manager in manager_users:
            Notification.objects.create(
                user=manager,
                notification_type=Notification.Type.SYSTEM,
                priority=Notification.Priority.HIGH,
                title="New approval request",
                message=f"{item.module}: {item.action} requires management review.",
                url="/approvals/",
            )
        AuditLog.objects.create(
            user=request.user, module=item.module, action=AuditLog.Action.CREATE,
            reference=item.reference or str(item.pk),
            description=f"Approval requested: {item.action}.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        messages.success(request, "Approval request submitted.")
        return redirect("core:approvals")
    return render(request, "core/form.html", {
        "title": "Request Approval", "form": form, "back_url": "core:approvals"
    })


@login_required
@role_required("super_admin", "institution_admin", "manager")
def approval_review(request, pk):
    item = get_object_or_404(ApprovalRequest, pk=pk)
    if item.status != ApprovalRequest.Status.PENDING:
        messages.info(request, "This approval request has already been reviewed.")
        return redirect("core:approvals")
    form = ApprovalReviewForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.save(update_fields=["status", "reviewer_note", "reviewed_by", "reviewed_at"])
        action = AuditLog.Action.APPROVE if item.status == ApprovalRequest.Status.APPROVED else AuditLog.Action.REJECT
        AuditLog.objects.create(
            user=request.user, module=item.module, action=action,
            reference=item.reference or str(item.pk),
            description=f"{item.action}: {item.reviewer_note}".strip(),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        messages.success(request, f"Approval request {item.get_status_display().lower()}.")
        return redirect("core:approvals")
    return render(request, "core/form.html", {
        "title": f"Review Approval · {item.reference or item.pk}",
        "form": form, "back_url": "core:approvals"
    })


@login_required
@role_required("super_admin", "institution_admin", "manager")
def audit_log(request):
    module = request.GET.get("module", "").strip()
    action = request.GET.get("action", "").strip()
    qs = AuditLog.objects.select_related("user")
    if module:
        qs = qs.filter(module__icontains=module)
    if action:
        qs = qs.filter(action=action)
    return render(request, "core/audit_log.html", {
        "title": "Audit Trail",
        "logs": qs[:300],
        "module": module,
        "selected_action": action,
        "action_choices": AuditLog.Action.choices,
    })
