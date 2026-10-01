from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.db.models import F, Avg, Q
from django.core.cache import cache
import json

from products.models import Product
from staff.models import StaffAttendance, StaffProfile, StaffTask, Designation, WorkArea, PerformanceRecord
from sales.models import Customer, Enquiry, SalesOrder, OrderRequest
from accounts.models import Notification, UserProfile, PushSubscription


def _user_payload(user):
    profile = getattr(user, "profile", None)
    customer_profile = getattr(user, "customer_profile", None)
    if customer_profile is not None:
        role = "customer"
        role_label = "Customer"
    else:
        role = UserProfile.Role.SUPER_ADMIN if user.is_superuser else getattr(profile, "role", UserProfile.Role.STAFF)
        role_label = "Super Admin" if user.is_superuser else (profile.get_role_display() if profile else "Staff")
    return {
        "id": user.id,
        "username": user.username,
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "role": role,
        "role_label": role_label,
        "is_superuser": user.is_superuser,
    }


def _notification_payload(notification):
    return {
        "id": notification.id,
        "type": notification.notification_type,
        "priority": notification.priority,
        "title": notification.title,
        "message": notification.message,
        "url": notification.url or "/",
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }


@require_GET
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)
    return JsonResponse({"authenticated": True, "user": _user_payload(request.user)})


@require_POST
def api_login(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid username or password."}, status=400)
    if not user.is_active:
        return JsonResponse({"detail": "This account is inactive."}, status=403)
    login(request, user)
    return JsonResponse({"authenticated": True, "user": _user_payload(user)})


@require_POST
@login_required
def api_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
@login_required
def dashboard_api(request):
    cache_key = f"dashboard_stats:{request.user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse({"user": _user_payload(request.user), "stats": cached})

    today = timezone.localdate()
    staff_qs = StaffProfile.objects.all()
    total_staff = staff_qs.count()
    active_staff = staff_qs.filter(status=StaffProfile.Status.ACTIVE).count()
    present_today = StaffAttendance.objects.filter(date=today, status=StaffAttendance.Status.PRESENT).count()
    stats = {
        "total_staff": total_staff,
        "active_staff": active_staff,
        "total_products": Product.objects.count(),
        "low_stock": Product.objects.filter(status=Product.Status.ACTIVE, stock_quantity__lte=F("low_stock_threshold")).count(),
        "open_tasks": StaffTask.objects.exclude(status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]).count(),
        "present_today": present_today,
        "attendance_rate": round((present_today / active_staff) * 100) if active_staff else 0,
        "customers": Customer.objects.filter(status=Customer.Status.ACTIVE).count(),
        "new_enquiries": Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
        "pending_requests": OrderRequest.objects.filter(status__in=[OrderRequest.Status.NEW, OrderRequest.Status.REVIEWING, OrderRequest.Status.CONTACTED, OrderRequest.Status.QUOTATION]).count(),
        "active_orders": SalesOrder.objects.exclude(status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]).count(),
    }
    cache.set(cache_key, stats, 15)
    return JsonResponse({"user": _user_payload(request.user), "stats": stats})


@require_GET
@login_required
def notifications_api(request):
    items = request.user.notifications.all()[:30]
    unread = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": unread, "notifications": [_notification_payload(n) for n in items]})


@require_POST
@login_required
def notification_read_api(request, notification_id):
    notification = request.user.notifications.filter(pk=notification_id).first()
    if not notification:
        return JsonResponse({"detail": "Notification not found."}, status=404)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"ok": True, "notification": _notification_payload(notification)})


@require_POST
@login_required
def notifications_read_all_api(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


@require_GET
@login_required
def push_config_api(request):
    from django.conf import settings
    return JsonResponse({
        "enabled": bool(getattr(settings, "WEB_PUSH_ENABLED", False)),
        "public_key": getattr(settings, "WEB_PUSH_PUBLIC_KEY", ""),
    })


@require_POST
@login_required
def push_subscribe_api(request):
    try:
        data = json.loads(request.body or "{}")
        endpoint = (data.get("endpoint") or "").strip()
        keys = data.get("keys") or {}
        p256dh = (keys.get("p256dh") or "").strip()
        auth = (keys.get("auth") or "").strip()
        if not endpoint or not p256dh or not auth:
            return JsonResponse({"ok": False, "detail": "Invalid push subscription."}, status=400)
        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={"user": request.user, "p256dh": p256dh, "auth": auth,
                      "user_agent": request.META.get("HTTP_USER_AGENT", "")[:4000], "is_active": True},
        )
        return JsonResponse({"ok": True, "subscription_id": subscription.pk})
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "detail": "Invalid JSON."}, status=400)


@require_POST
@login_required
def push_unsubscribe_api(request):
    try:
        data = json.loads(request.body or "{}")
    except (ValueError, TypeError, json.JSONDecodeError):
        data = {}
    endpoint = (data.get("endpoint") or "").strip()
    qs = PushSubscription.objects.filter(user=request.user)
    if endpoint:
        qs = qs.filter(endpoint=endpoint)
    qs.update(is_active=False)
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Staff Management API (React migration)
# ---------------------------------------------------------------------------
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods
from staff.services import staff_for_user, can_manage_staff, task_queryset_for_user, attendance_queryset_for_user, performance_queryset_for_user
from staff.decorators import staff_manager_required


def _staff_payload(profile):
    return {
        "id": profile.id,
        "staff_id": profile.staff_id,
        "name": profile.user.get_full_name() or profile.user.username,
        "username": profile.user.username,
        "email": profile.user.email,
        "first_name": profile.user.first_name,
        "last_name": profile.user.last_name,
        "phone": profile.phone,
        "address": profile.address,
        "joining_date": profile.joining_date.isoformat() if profile.joining_date else None,
        "status": profile.status,
        "status_label": profile.get_status_display(),
        "designation": {"id": profile.designation_id, "name": profile.designation.name} if profile.designation else None,
        "work_area": {"id": profile.work_area_id, "name": profile.work_area.name} if profile.work_area else None,
        "photo": profile.photo.url if profile.photo else None,
        "notes": profile.notes,
    }


def _choice_payload(qs):
    return [{"id": x.id, "name": x.name} for x in qs]


@require_GET
@login_required
def staff_api(request):
    qs = staff_for_user(request.user)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    designation = request.GET.get("designation", "").strip()
    work_area = request.GET.get("work_area", "").strip()
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__username__icontains=q) | Q(staff_id__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if designation:
        qs = qs.filter(designation_id=designation)
    if work_area:
        qs = qs.filter(work_area_id=work_area)
    stats = {
        "total": qs.count(),
        "active": qs.filter(status=StaffProfile.Status.ACTIVE).count(),
        "inactive": qs.filter(status=StaffProfile.Status.INACTIVE).count(),
        "on_leave": qs.filter(status=StaffProfile.Status.ON_LEAVE).count(),
    }
    return JsonResponse({"staff": [_staff_payload(x) for x in qs], "stats": stats,
                         "designations": _choice_payload(Designation.objects.filter(is_active=True)),
                         "work_areas": _choice_payload(WorkArea.objects.filter(is_active=True)),
                         "can_manage": can_manage_staff(request.user)})


@require_GET
@login_required
def staff_detail_api(request, pk):
    profile = get_object_or_404(staff_for_user(request.user), pk=pk)
    tasks = profile.tasks.select_related("assigned_by").order_by("-created_at")[:10]
    attendance = profile.attendance.order_by("-date")[:10]
    performance = profile.performance_records.select_related("evaluator").order_by("-review_date")[:10]
    task_total = profile.tasks.count()
    task_completed = profile.tasks.filter(status=StaffTask.Status.COMPLETED).count()
    attendance_total = profile.attendance.count()
    attendance_present = profile.attendance.filter(status=StaffAttendance.Status.PRESENT).count()
    avg_score = profile.performance_records.aggregate(value=Avg("score"))["value"] or 0
    task_rate = round(task_completed * 100 / task_total) if task_total else 0
    attendance_rate = round(attendance_present * 100 / attendance_total) if attendance_total else 0
    kpi = round(task_rate*.4 + attendance_rate*.3 + float(avg_score)*.3) if (task_total or attendance_total or avg_score) else 0
    return JsonResponse({"staff": _staff_payload(profile), "kpi": {"task_rate": task_rate, "attendance_rate": attendance_rate, "average_review": round(float(avg_score),1), "score": min(kpi,100)},
        "tasks": [{"id":t.id,"title":t.title,"status":t.status,"status_label":t.get_status_display(),"priority":t.priority,"priority_label":t.get_priority_display(),"due_date":t.due_date.isoformat() if t.due_date else None} for t in tasks],
        "attendance": [{"id":a.id,"date":a.date.isoformat(),"status":a.status,"status_label":a.get_status_display(),"remarks":a.remarks} for a in attendance],
        "performance": [{"id":r.id,"review_date":r.review_date.isoformat(),"score":r.score,"strengths":r.strengths,"improvements":r.improvements,"remarks":r.remarks,"evaluator":r.evaluator.get_full_name() if r.evaluator else None} for r in performance]})


@require_GET
@login_required
def staff_options_api(request):
    return JsonResponse({"staff": [{"id":s.id,"name":str(s)} for s in staff_for_user(request.user).filter(status=StaffProfile.Status.ACTIVE)],
                         "designations": _choice_payload(Designation.objects.filter(is_active=True)),
                         "work_areas": _choice_payload(WorkArea.objects.filter(is_active=True))})


@require_POST
@staff_manager_required
def staff_create_api(request):
    data = request.POST
    required = ["username", "password", "first_name", "staff_id"]
    missing = [x for x in required if not str(data.get(x, "")).strip()]
    if missing: return JsonResponse({"detail": f"Missing required fields: {', '.join(missing)}"}, status=400)
    if User.objects.filter(username=data["username"]).exists(): return JsonResponse({"detail":"Username already exists."}, status=400)
    if StaffProfile.objects.filter(staff_id=data["staff_id"]).exists(): return JsonResponse({"detail":"Staff ID already exists."}, status=400)
    try:
        with transaction.atomic():
            user=User.objects.create_user(username=data["username"],password=data["password"],first_name=data.get("first_name", ""),last_name=data.get("last_name", ""),email=data.get("email", ""))
            from accounts.models import UserProfile
            UserProfile.objects.create(user=user, role=UserProfile.Role.STAFF)
            profile=StaffProfile.objects.create(user=user,staff_id=data["staff_id"],designation_id=data.get("designation") or None,work_area_id=data.get("work_area") or None,phone=data.get("phone",""),joining_date=parse_date(data.get("joining_date")) if data.get("joining_date") else None,address=data.get("address",""),status=data.get("status") or StaffProfile.Status.ACTIVE,notes=data.get("notes",""),photo=request.FILES.get("photo"))
    except Exception as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"staff": _staff_payload(profile)}, status=201)


@require_POST
@staff_manager_required
def staff_update_api(request, pk):
    profile=get_object_or_404(staff_for_user(request.user), pk=pk)
    data=request.POST
    if data.get("staff_id") and StaffProfile.objects.filter(staff_id=data["staff_id"]).exclude(pk=pk).exists(): return JsonResponse({"detail":"Staff ID already exists."},status=400)
    profile.staff_id=data.get("staff_id",profile.staff_id); profile.designation_id=data.get("designation") or None; profile.work_area_id=data.get("work_area") or None; profile.phone=data.get("phone",profile.phone); profile.address=data.get("address",profile.address); profile.status=data.get("status",profile.status); profile.notes=data.get("notes",profile.notes)
    if data.get("joining_date"): profile.joining_date=parse_date(data["joining_date"])
    if "photo" in request.FILES: profile.photo=request.FILES["photo"]
    profile.save()
    user=profile.user; user.first_name=data.get("first_name",user.first_name); user.last_name=data.get("last_name",user.last_name); user.email=data.get("email",user.email); user.save(update_fields=["first_name","last_name","email"])
    return JsonResponse({"staff":_staff_payload(profile)})


def _task_payload(t):
    return {"id":t.id,"title":t.title,"description":t.description,"assigned_to":{"id":t.assigned_to_id,"name":str(t.assigned_to)},"due_date":t.due_date.isoformat() if t.due_date else None,"priority":t.priority,"priority_label":t.get_priority_display(),"status":t.status,"status_label":t.get_status_display(),"remarks":t.remarks,"completed_at":t.completed_at.isoformat() if t.completed_at else None}


@require_GET
@login_required
def staff_tasks_api(request):
    qs=task_queryset_for_user(request.user)
    status=request.GET.get("status","").strip(); q=request.GET.get("q","").strip()
    if status: qs=qs.filter(status=status)
    if q: qs=qs.filter(Q(title__icontains=q)|Q(description__icontains=q))
    return JsonResponse({"tasks":[_task_payload(t) for t in qs],"can_manage":can_manage_staff(request.user),"staff":[{"id":s.id,"name":str(s)} for s in staff_for_user(request.user).filter(status=StaffProfile.Status.ACTIVE)]})


@require_POST
@login_required
def staff_task_status_api(request, pk):
    task=get_object_or_404(task_queryset_for_user(request.user),pk=pk)
    status=str(request.POST.get("status","")).strip()
    if status not in dict(StaffTask.Status.choices): return JsonResponse({"detail":"Invalid status."},status=400)
    task.status=status
    from django.utils import timezone
    task.completed_at=timezone.now() if status==StaffTask.Status.COMPLETED else None
    task.save(update_fields=["status","completed_at","updated_at"])
    return JsonResponse({"task":_task_payload(task)})


@require_POST
@staff_manager_required
def staff_task_create_api(request):
    task=StaffTask.objects.create(title=request.POST.get("title",""),description=request.POST.get("description",""),assigned_to_id=request.POST.get("assigned_to"),assigned_by=request.user,due_date=parse_date(request.POST["due_date"]) if request.POST.get("due_date") else None,priority=request.POST.get("priority",StaffTask.Priority.MEDIUM),status=request.POST.get("status",StaffTask.Status.TODO),remarks=request.POST.get("remarks",""))
    return JsonResponse({"task":_task_payload(task)},status=201)


@require_GET
@login_required
def staff_attendance_api(request):
    qs=attendance_queryset_for_user(request.user); return JsonResponse({"records":[{"id":a.id,"staff_id":a.staff_id,"staff":str(a.staff),"date":a.date.isoformat(),"status":a.status,"status_label":a.get_status_display(),"remarks":a.remarks} for a in qs],"can_manage":can_manage_staff(request.user)})


@require_POST
@staff_manager_required
def staff_attendance_create_api(request):
    staff_id=request.POST.get("staff"); day=parse_date(request.POST.get("date",""));
    if not staff_id or not day: return JsonResponse({"detail":"Staff and date are required."},status=400)
    if StaffAttendance.objects.filter(staff_id=staff_id,date=day).exists(): return JsonResponse({"detail":"Attendance already exists for this date."},status=400)
    record=StaffAttendance.objects.create(staff_id=staff_id,date=day,status=request.POST.get("status",StaffAttendance.Status.PRESENT),remarks=request.POST.get("remarks",""),marked_by=request.user)
    return JsonResponse({"id":record.id},status=201)


@require_GET
@login_required
def staff_performance_api(request):
    qs=performance_queryset_for_user(request.user); return JsonResponse({"records":[{"id":r.id,"staff_id":r.staff_id,"staff":str(r.staff),"review_date":r.review_date.isoformat(),"score":r.score,"strengths":r.strengths,"improvements":r.improvements,"remarks":r.remarks} for r in qs],"can_manage":can_manage_staff(request.user)})


@require_POST
@staff_manager_required
def staff_performance_create_api(request):
    record=PerformanceRecord.objects.create(staff_id=request.POST.get("staff"),review_date=parse_date(request.POST.get("review_date","")),score=int(request.POST.get("score",0)),strengths=request.POST.get("strengths",""),improvements=request.POST.get("improvements",""),remarks=request.POST.get("remarks",""),evaluator=request.user)
    return JsonResponse({"id":record.id},status=201)

# ---------------------------------------------------------------------------
# Products / Inventory API (React migration - Phase 4)
# ---------------------------------------------------------------------------
from decimal import Decimal, InvalidOperation
from products.models import ProductCategory, StockTransaction
from products.services import can_manage_products, product_queryset, dashboard_stats
from products.inventory import record_stock_transaction


def _category_payload(category):
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "is_active": category.is_active,
        "parent": {"id": category.parent_id, "name": category.parent.name} if category.parent else None,
        "is_section": category.is_section,
        "product_count": category.products.filter(customer_visible=False).count(),
    }


def _product_payload(product):
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category": {"id": product.category_id, "name": product.category.name} if product.category else None,
        "description": product.description,
        "unit": product.unit,
        "cost_price": str(product.cost_price),
        "stock_quantity": str(product.stock_quantity),
        "low_stock_threshold": str(product.low_stock_threshold),
        "status": product.status,
        "status_label": product.get_status_display(),
        "is_low_stock": product.is_low_stock,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }


def _stock_payload(tx):
    return {
        "id": tx.id,
        "product": {"id": tx.product_id, "name": tx.product.name, "sku": tx.product.sku},
        "transaction_type": tx.transaction_type,
        "transaction_type_label": tx.get_transaction_type_display(),
        "quantity": str(tx.quantity),
        "balance_after": str(tx.balance_after),
        "reference": tx.reference,
        "remarks": tx.remarks,
        "created_by": tx.created_by.get_full_name() or tx.created_by.username if tx.created_by else None,
        "created_at": tx.created_at.isoformat(),
    }


@require_GET
@login_required
def products_api(request):
    qs = product_queryset()
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()
    low_stock = request.GET.get("low_stock", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(category__name__icontains=q))
    if category:
        qs = qs.filter(category_id=category)
    if status:
        qs = qs.filter(status=status)
    if low_stock == "1":
        qs = qs.filter(stock_quantity__lte=F("low_stock_threshold"), status=Product.Status.ACTIVE)
    categories = ProductCategory.objects.filter(parent__isnull=True, is_section=False, is_active=True).order_by("name")
    return JsonResponse({
        "products": [_product_payload(p) for p in qs],
        "stats": dashboard_stats(),
        "categories": [_category_payload(c) for c in categories],
        "can_manage": can_manage_products(request.user),
    })


@require_GET
@login_required
def product_detail_api(request, pk):
    product = get_object_or_404(product_queryset(), pk=pk)
    transactions = product.stock_transactions.select_related("created_by").order_by("-created_at")[:20]
    return JsonResponse({"product": _product_payload(product), "transactions": [_stock_payload(t) for t in transactions], "can_manage": can_manage_products(request.user)})


def _request_data(request):
    if request.content_type and "multipart/form-data" in request.content_type:
        return request.POST
    try:
        return json.loads(request.body or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _decimal(data, key, default="0"):
    value = data.get(key, default)
    try:
        return Decimal(str(value if value not in (None, "") else default))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{key} must be a valid number.")


@require_POST
@login_required
def product_create_api(request):
    if not can_manage_products(request.user):
        return JsonResponse({"detail": "You do not have permission to manage products."}, status=403)
    data = _request_data(request)
    required = ["name", "sku", "category"]
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        return JsonResponse({"detail": f"Missing fields: {', '.join(missing)}."}, status=400)
    sku = str(data["sku"]).strip().upper()
    if Product.objects.filter(sku=sku).exists():
        return JsonResponse({"detail": "SKU already exists."}, status=400)
    category = get_object_or_404(ProductCategory, pk=data["category"], parent__isnull=True, is_section=False, is_active=True)
    try:
        product = Product.objects.create(
            name=str(data["name"]).strip(), sku=sku, category=category,
            description=str(data.get("description", "")).strip(), unit=str(data.get("unit", "Piece")).strip() or "Piece",
            cost_price=_decimal(data, "cost_price"), stock_quantity=_decimal(data, "stock_quantity"),
            low_stock_threshold=_decimal(data, "low_stock_threshold"), customer_visible=False,
            selling_price=0, actual_price=0, discount_price=0,
            status=str(data.get("status", Product.Status.ACTIVE)),
        )
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"ok": True, "product": _product_payload(product)}, status=201)


@require_POST
@login_required
def product_update_api(request, pk):
    if not can_manage_products(request.user):
        return JsonResponse({"detail": "You do not have permission to manage products."}, status=403)
    product = get_object_or_404(product_queryset(), pk=pk)
    data = _request_data(request)
    sku = str(data.get("sku", product.sku)).strip().upper()
    if Product.objects.filter(sku=sku).exclude(pk=pk).exists():
        return JsonResponse({"detail": "SKU already exists."}, status=400)
    try:
        product.name = str(data.get("name", product.name)).strip()
        product.sku = sku
        if data.get("category"):
            product.category = get_object_or_404(ProductCategory, pk=data["category"], parent__isnull=True, is_section=False, is_active=True)
        product.description = str(data.get("description", product.description)).strip()
        product.unit = str(data.get("unit", product.unit)).strip() or "Piece"
        product.cost_price = _decimal(data, "cost_price", product.cost_price)
        product.low_stock_threshold = _decimal(data, "low_stock_threshold", product.low_stock_threshold)
        if "status" in data and data.get("status") in dict(Product.Status.choices):
            product.status = data.get("status")
        product.customer_visible = False
        product.selling_price = product.actual_price = product.discount_price = 0
        product.save()
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"ok": True, "product": _product_payload(product)})


@require_GET
@login_required
def product_categories_api(request):
    qs = ProductCategory.objects.filter(parent__isnull=True, is_section=False).order_by("name")
    return JsonResponse({"categories": [_category_payload(c) for c in qs], "can_manage": can_manage_products(request.user)})


@require_POST
@login_required
def product_category_create_api(request):
    if not can_manage_products(request.user):
        return JsonResponse({"detail": "You do not have permission to manage product categories."}, status=403)
    data = _request_data(request)
    name = str(data.get("name", "")).strip()
    if not name:
        return JsonResponse({"detail": "Category name is required."}, status=400)
    if ProductCategory.objects.filter(name__iexact=name).exists():
        return JsonResponse({"detail": "A category with this name already exists."}, status=400)
    category = ProductCategory.objects.create(name=name, description=str(data.get("description", "")).strip(), is_active=True, is_section=False)
    return JsonResponse({"ok": True, "category": _category_payload(category)}, status=201)


@require_POST
@login_required
def stock_transaction_api(request):
    if not can_manage_products(request.user):
        return JsonResponse({"detail": "You do not have permission to manage stock."}, status=403)
    data = _request_data(request)
    try:
        product_id = int(data.get("product"))
        quantity = _decimal(data, "quantity")
        transaction_type = str(data.get("transaction_type", "")).strip()
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if transaction_type not in dict(StockTransaction.TransactionType.choices):
            raise ValueError("Invalid stock transaction type.")
        product = get_object_or_404(Product, pk=product_id, customer_visible=False, status=Product.Status.ACTIVE)
        tx = record_stock_transaction(product_id=product.id, transaction_type=transaction_type, quantity=quantity,
                                      user=request.user, reference=str(data.get("reference", "")).strip(),
                                      remarks=str(data.get("remarks", "")).strip())
    except (ValueError, TypeError, InvalidOperation, ValidationError) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"ok": True, "transaction": _stock_payload(tx), "product": _product_payload(tx.product)})


@require_GET
@login_required
def stock_transactions_api(request):
    qs = StockTransaction.objects.select_related("product", "created_by")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(reference__icontains=q))
    product = request.GET.get("product", "").strip()
    if product:
        qs = qs.filter(product_id=product)
    return JsonResponse({"transactions": [_stock_payload(t) for t in qs[:200]], "can_manage": can_manage_products(request.user)})


# ---------------------------------------------------------------------------
# Final React migration APIs: users, profile, approvals, audit, requests
# ---------------------------------------------------------------------------
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from accounts.services import can_assign_role, can_manage_target, get_or_create_profile, update_user, available_roles
from core.models import ApprovalRequest, AuditLog


def _user_admin_payload(user):
    profile = get_or_create_profile(user)
    return {
        "id": user.id, "username": user.username,
        "name": user.get_full_name() or user.username,
        "first_name": user.first_name, "last_name": user.last_name,
        "email": user.email, "phone": profile.phone,
        "role": profile.role, "role_label": profile.get_role_display(),
        "is_active": bool(user.is_active and profile.is_active),
        "created_at": user.date_joined.isoformat() if user.date_joined else None,
    }


def _can_manage_users(user):
    return user.is_superuser or getattr(getattr(user, "profile", None), "role", None) in (
        UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN
    )


@require_GET
@login_required

def users_api(request):
    if not _can_manage_users(request.user):
        return JsonResponse({"detail": "You do not have permission to manage users."}, status=403)
    qs = User.objects.select_related("profile").order_by("username")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if role:
        qs = qs.filter(profile__role=role)
    if status == "active":
        qs = qs.filter(is_active=True, profile__is_active=True)
    elif status == "inactive":
        qs = qs.filter(Q(is_active=False) | Q(profile__is_active=False))
    all_users = User.objects.select_related("profile")
    return JsonResponse({
        "users": [_user_admin_payload(u) for u in qs],
        "active_count": all_users.filter(is_active=True, profile__is_active=True).count(),
        "roles": [{"value": v, "label": l} for v, l in UserProfile.Role.choices],
        "can_manage": True,
    })


@require_POST
@login_required

def user_create_api(request):
    if not _can_manage_users(request.user):
        return JsonResponse({"detail": "You do not have permission to manage users."}, status=403)
    data = _request_data(request)
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    role = str(data.get("role", UserProfile.Role.STAFF)).strip()
    if not username or not password:
        return JsonResponse({"detail": "Username and password are required."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"detail": "Username already exists."}, status=400)
    if role not in dict(UserProfile.Role.choices) or not can_assign_role(request.user, role):
        return JsonResponse({"detail": "You cannot assign this role."}, status=403)
    user = User.objects.create_user(username=username, password=password,
        first_name=str(data.get("first_name", "")).strip(), last_name=str(data.get("last_name", "")).strip(),
        email=str(data.get("email", "")).strip())
    get_or_create_profile(user)
    update_user(user=user, role=role, first_name=user.first_name, last_name=user.last_name,
        email=user.email, phone=str(data.get("phone", "")).strip(), is_active=True)
    return JsonResponse({"ok": True, "user": _user_admin_payload(user)}, status=201)


@require_POST
@login_required

def user_update_api(request, pk):
    if not _can_manage_users(request.user):
        return JsonResponse({"detail": "You do not have permission to manage users."}, status=403)
    target = get_object_or_404(User, pk=pk)
    if not can_manage_target(request.user, target):
        return JsonResponse({"detail": "You cannot manage this user."}, status=403)
    data = _request_data(request)
    role = str(data.get("role", get_or_create_profile(target).role)).strip()
    active = str(data.get("is_active", "true")).lower() not in ("false", "0", "no")
    if target == request.user and not active:
        return JsonResponse({"detail": "You cannot deactivate your own account."}, status=400)
    if role not in dict(UserProfile.Role.choices) or not can_assign_role(request.user, role):
        return JsonResponse({"detail": "You cannot assign this role."}, status=403)
    update_user(user=target, role=role,
        first_name=str(data.get("first_name", target.first_name)).strip(),
        last_name=str(data.get("last_name", target.last_name)).strip(),
        email=str(data.get("email", target.email)).strip(),
        phone=str(data.get("phone", get_or_create_profile(target).phone)).strip(),
        is_active=active)
    return JsonResponse({"ok": True, "user": _user_admin_payload(target)})


@require_POST
@login_required

def profile_update_api(request):
    data = _request_data(request)
    user = request.user
    profile = get_or_create_profile(user)
    user.first_name = str(data.get("first_name", user.first_name)).strip()
    user.last_name = str(data.get("last_name", user.last_name)).strip()
    user.email = str(data.get("email", user.email)).strip()
    user.save(update_fields=["first_name", "last_name", "email"])
    profile.phone = str(data.get("phone", profile.phone)).strip()
    profile.save(update_fields=["phone", "updated_at"])
    return JsonResponse({"ok": True, "user": _user_payload(user)})


def _approval_payload(item):
    return {"id": item.id, "module": item.module, "action": item.action, "reference": item.reference,
        "amount": str(item.amount), "reason": item.reason, "status": item.status,
        "status_label": item.get_status_display(), "requested_by": item.requested_by.get_full_name() if item.requested_by else None,
        "reviewed_by": item.reviewed_by.get_full_name() if item.reviewed_by else None,
        "reviewer_note": item.reviewer_note, "created_at": item.created_at.isoformat(),
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None}


@require_GET
@login_required

def approvals_api(request):
    if getattr(getattr(request.user, "profile", None), "role", None) not in ("super_admin", "institution_admin", "manager") and not request.user.is_superuser:
        return JsonResponse({"detail": "You do not have permission to view approvals."}, status=403)
    qs = ApprovalRequest.objects.select_related("requested_by", "reviewed_by")
    status = request.GET.get("status", "").strip()
    if status: qs = qs.filter(status=status)
    return JsonResponse({"items": [_approval_payload(x) for x in qs[:300]], "can_review": True})


@require_POST
@login_required

def approval_review_api(request, pk):
    if getattr(getattr(request.user, "profile", None), "role", None) not in ("super_admin", "institution_admin", "manager") and not request.user.is_superuser:
        return JsonResponse({"detail": "You do not have permission to review approvals."}, status=403)
    item = get_object_or_404(ApprovalRequest, pk=pk)
    data = _request_data(request)
    status = str(data.get("status", "")).strip()
    if status not in (ApprovalRequest.Status.APPROVED, ApprovalRequest.Status.REJECTED):
        return JsonResponse({"detail": "Status must be approved or rejected."}, status=400)
    item.status = status
    item.reviewer_note = str(data.get("reviewer_note", "")).strip()
    item.reviewed_by = request.user
    item.reviewed_at = timezone.now()
    item.save(update_fields=["status", "reviewer_note", "reviewed_by", "reviewed_at"])
    AuditLog.objects.create(user=request.user, module=item.module,
        action=AuditLog.Action.APPROVE if status == ApprovalRequest.Status.APPROVED else AuditLog.Action.REJECT,
        reference=item.reference or str(item.pk), description=f"{item.action}: {item.reviewer_note}".strip(),
        ip_address=request.META.get("REMOTE_ADDR"))
    return JsonResponse({"ok": True, "item": _approval_payload(item)})


@require_GET
@login_required

def audit_api(request):
    if getattr(getattr(request.user, "profile", None), "role", None) not in ("super_admin", "institution_admin", "manager") and not request.user.is_superuser:
        return JsonResponse({"detail": "You do not have permission to view audit logs."}, status=403)
    qs = AuditLog.objects.select_related("user")
    module = request.GET.get("module", "").strip(); action = request.GET.get("action", "").strip()
    if module: qs = qs.filter(module__icontains=module)
    if action: qs = qs.filter(action=action)
    return JsonResponse({"items": [{"id": x.id, "user": x.user.get_full_name() if x.user else None,
        "module": x.module, "action": x.action, "action_label": x.get_action_display(),
        "reference": x.reference, "description": x.description, "ip_address": x.ip_address,
        "created_at": x.created_at.isoformat()} for x in qs[:500]]})


@require_GET
@login_required

def customer_requests_api(request):
    qs = OrderRequest.objects.select_related("customer", "product", "assigned_to")
    role = getattr(getattr(request.user, "profile", None), "role", None)
    if role == UserProfile.Role.STAFF and not request.user.is_superuser:
        qs = qs.filter(assigned_to=request.user)
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip()
    if q: qs = qs.filter(Q(request_no__icontains=q) | Q(customer__name__icontains=q) | Q(product_name__icontains=q))
    if status: qs = qs.filter(status=status)
    return JsonResponse({"items": [{"id": x.id, "request_no": x.request_no, "customer": x.customer.name,
        "product": x.product.name if x.product else x.product_name, "quantity": str(x.quantity), "requirement": x.requirement,
        "status": x.status, "status_label": x.get_status_display(), "assigned_to": x.assigned_to.get_full_name() if x.assigned_to else None,
        "requested_date": x.requested_date.isoformat() if x.requested_date else None, "budget": x.budget,
        "manager_notes": x.manager_notes, "created_at": x.created_at.isoformat()} for x in qs[:300]]})


@require_POST
@login_required

def customer_request_update_api(request, pk):
    item = get_object_or_404(OrderRequest, pk=pk)
    role = getattr(getattr(request.user, "profile", None), "role", None)
    if role == UserProfile.Role.STAFF and item.assigned_to_id != request.user.id:
        return JsonResponse({"detail": "You cannot update this request."}, status=403)
    data = _request_data(request)
    status = str(data.get("status", item.status)).strip()
    if status not in dict(OrderRequest.Status.choices): return JsonResponse({"detail": "Invalid status."}, status=400)
    item.status = status
    item.manager_notes = str(data.get("manager_notes", item.manager_notes)).strip()
    if data.get("assigned_to") and role != UserProfile.Role.STAFF:
        item.assigned_to_id = data.get("assigned_to")
    item.save(update_fields=["status", "manager_notes", "assigned_to", "updated_at"])
    return JsonResponse({"ok": True})
