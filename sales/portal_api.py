import json
from decimal import Decimal
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Customer, CustomerNotification, CustomerFeedback, DesignApproval, DeliveryRecord, OrderRequest, Quotation, SalesOrder
from products.models import Product


def _customer(request):
    return getattr(request.user, "customer_profile", None)

def _guard_customer(request):
    customer = _customer(request)
    if not request.user.is_authenticated or customer is None:
        return None
    return customer

def _product(p):
    return {"id": p.id, "name": p.name, "sku": getattr(p, "sku", ""), "description": getattr(p, "description", ""), "price": str(getattr(p, "customer_price", getattr(p, "selling_price", 0))), "stock": str(getattr(p, "stock_quantity", 0)), "image": p.image.url if getattr(p, "image", None) else None}

def _notification(n):
    return {"id": n.id, "type": n.notification_type, "title": n.title, "message": n.message, "is_read": n.is_read, "created_at": n.created_at.isoformat()}

def _request(o):
    return {"id": o.id, "request_no": o.request_no, "request_type": o.request_type, "product_name": o.product_name or (o.product.name if o.product_id else ""), "quantity": str(o.quantity), "size": o.size, "material_preference": o.material_preference, "requirement": o.requirement, "budget": o.budget, "requested_date": o.requested_date.isoformat() if o.requested_date else None, "design_requirement": o.design_requirement, "status": o.status, "manager_notes": o.manager_notes, "created_at": o.created_at.isoformat()}

def _quotation(q):
    designs = [{"id": d.id, "version": d.version, "status": d.status, "notes": d.notes, "customer_notes": d.customer_notes, "file": d.file.url if d.file else None} for d in q.designs.all()]
    return {"id": q.id, "quotation_no": q.quotation_no, "item_description": q.item_description, "quantity": str(q.quantity), "quoted_price": str(q.quoted_price), "advance_required": str(q.advance_required), "delivery_timeline": q.delivery_timeline, "valid_until": q.valid_until.isoformat() if q.valid_until else None, "status": q.status, "notes": q.notes, "designs": designs}

def _order(o):
    received = sum((p.amount for p in o.payments.all() if p.status in ("received", "verified")), Decimal("0"))
    delivery = getattr(o, "delivery", None)
    feedback = getattr(o, "feedback", None)
    return {"id": o.id, "order_no": o.order_no, "item_description": o.item_description, "quantity": str(o.quantity), "confirmed_price": str(o.confirmed_price), "advance_required": str(o.advance_required), "status": o.status, "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None, "deadline": o.deadline.isoformat() if o.deadline else None, "payment_received": str(received), "balance": str(o.confirmed_price - received), "delivery": ({"status": delivery.status, "delivery_date": delivery.delivery_date.isoformat() if delivery.delivery_date else None, "address": delivery.address, "installation_required": delivery.installation_required} if delivery else None), "feedback": ({"rating": feedback.rating, "comment": feedback.comment} if feedback else None)}

@require_http_methods(["POST"])
def portal_register(request):
    data = json.loads(request.body or "{}")
    name, phone, email, password = map(lambda k: str(data.get(k, "")).strip(), ["name", "phone", "email", "password"])
    if not name or not phone or len(password) < 6: return JsonResponse({"detail": "Name, phone and a password of at least 6 characters are required."}, status=400)
    if Customer.objects.filter(phone=phone, user__isnull=False).exists(): return JsonResponse({"detail": "A customer account already exists for this phone number."}, status=400)
    username = "c_" + "".join(ch for ch in phone if ch.isalnum())
    base = username; i = 1
    while User.objects.filter(username=username).exists(): i += 1; username = f"{base}_{i}"
    user = User.objects.create_user(username=username, password=password, email=email, first_name=name)
    customer = Customer.objects.filter(phone=phone, user__isnull=True).first()
    if customer:
        customer.user, customer.name, customer.email = user, name, email; customer.save(update_fields=["user","name","email","updated_at"])
    else: customer = Customer.objects.create(user=user, name=name, phone=phone, email=email)
    login(request, user)
    return JsonResponse({"ok": True, "username": username})

@login_required
def portal_summary(request):
    c = _guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"customer":{"id":c.id,"name":c.name,"phone":c.phone,"email":c.email,"address":c.address},"stats":{"requests":c.order_requests.count(),"quotations":c.quotations.count(),"orders":c.orders.count(),"unread_notifications":c.user.customer_notifications.filter(is_read=False).count()}})

@login_required
@require_http_methods(["GET","POST"])
def portal_profile(request):
    c = _guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    if request.method == "POST":
        data=json.loads(request.body or "{}"); c.name=str(data.get("name",c.name)).strip(); c.email=str(data.get("email",c.email)).strip(); c.address=str(data.get("address",c.address)).strip(); c.alternate_phone=str(data.get("alternate_phone",c.alternate_phone)).strip(); c.save(update_fields=["name","email","address","alternate_phone","updated_at"]); c.user.first_name=c.name; c.user.email=c.email; c.user.save(update_fields=["first_name","email"])
    return JsonResponse({"customer":{"id":c.id,"name":c.name,"phone":c.phone,"email":c.email,"alternate_phone":c.alternate_phone,"address":c.address}})

@login_required
def portal_products(request):
    if not _guard_customer(request): return JsonResponse({"detail":"Customer account required."}, status=403)
    qs=Product.objects.filter(status=Product.Status.ACTIVE, customer_visible=True).order_by("name")[:250]
    return JsonResponse({"products":[_product(p) for p in qs]})

@login_required
def portal_product_detail(request, pk):
    if not _guard_customer(request): return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"product":_product(get_object_or_404(Product, pk=pk, status=Product.Status.ACTIVE, customer_visible=True))})

@login_required
def portal_notifications(request):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"notifications":[_notification(n) for n in c.user.customer_notifications.all()[:50]]})

@login_required
@require_http_methods(["POST"])
def portal_notification_read(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    n=get_object_or_404(CustomerNotification, pk=pk, user=c.user); n.is_read=True; n.save(update_fields=["is_read"]); return JsonResponse({"ok":True})

@login_required
def portal_requests(request):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"requests":[_request(x) for x in c.order_requests.all()]})

@login_required
@require_http_methods(["POST"])
def portal_request_create(request):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    data=json.loads(request.body or "{}"); obj=OrderRequest(customer=c, product_id=data.get("product_id") or None, product_name=str(data.get("product_name","")).strip(), quantity=data.get("quantity") or 1, size=str(data.get("size","")).strip(), material_preference=str(data.get("material_preference","")).strip(), requirement=str(data.get("requirement","")).strip(), budget=str(data.get("budget","")).strip(), requested_date=data.get("requested_date") or None, design_requirement=str(data.get("design_requirement","")).strip(), request_type=str(data.get("request_type","enquiry")))
    if not obj.requirement: return JsonResponse({"detail":"Requirement is required."}, status=400)
    obj.save(); return JsonResponse({"request":_request(obj)}, status=201)

@login_required
def portal_request_detail(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"request":_request(get_object_or_404(OrderRequest,pk=pk,customer=c))})

@login_required
def portal_quotations(request):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"quotations":[_quotation(x) for x in c.quotations.prefetch_related("designs").all()]})

@login_required
def portal_quotation_detail(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"quotation":_quotation(get_object_or_404(Quotation.objects.prefetch_related("designs"),pk=pk,customer=c))})

@login_required
@require_http_methods(["POST"])
def portal_quotation_response(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    q=get_object_or_404(Quotation,pk=pk,customer=c); data=json.loads(request.body or "{}"); decision=data.get("decision")
    if decision not in (Quotation.Status.APPROVED, Quotation.Status.REJECTED): return JsonResponse({"detail":"Invalid quotation response."}, status=400)
    q.status=decision; q.save(update_fields=["status","updated_at"]); return JsonResponse({"quotation":_quotation(q)})

@login_required
@require_http_methods(["POST"])
def portal_design_response(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    d=get_object_or_404(DesignApproval,pk=pk,quotation__customer=c); data=json.loads(request.body or "{}"); decision=data.get("decision")
    if decision not in (DesignApproval.Status.APPROVED, DesignApproval.Status.REVISION): return JsonResponse({"detail":"Invalid design response."}, status=400)
    d.status=decision; d.customer_notes=str(data.get("customer_notes","")).strip(); d.responded_at=timezone.now(); d.save(update_fields=["status","customer_notes","responded_at","updated_at"]); return JsonResponse({"ok":True})

@login_required
def portal_orders(request):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"orders":[_order(x) for x in c.orders.prefetch_related("payments").select_related("delivery","feedback").all()]})

@login_required
def portal_order_detail(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    return JsonResponse({"order":_order(get_object_or_404(SalesOrder.objects.prefetch_related("payments").select_related("delivery","feedback"),pk=pk,customer=c))})

@login_required
@require_http_methods(["POST"])
def portal_feedback(request, pk):
    c=_guard_customer(request)
    if not c: return JsonResponse({"detail":"Customer account required."}, status=403)
    o=get_object_or_404(SalesOrder,pk=pk,customer=c,status=SalesOrder.Status.DELIVERED); data=json.loads(request.body or "{}"); rating=int(data.get("rating") or 0)
    if rating < 1 or rating > 5: return JsonResponse({"detail":"Rating must be between 1 and 5."}, status=400)
    fb,_=CustomerFeedback.objects.update_or_create(order=o,defaults={"rating":rating,"comment":str(data.get("comment","")).strip()}); return JsonResponse({"ok":True,"rating":fb.rating})
