import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from accounts.models import UserProfile
from products.models import Product
from .api import _customer_qs, _global_admin, _manager, _quotation_qs
from .models import Customer, Quotation, QuotationApproval, QuotationConfiguration, QuotationLineItem
from .quotation_services import quotation_pdf_response

CENT = Decimal("0.01")


def _founder(user):
    profile = getattr(user, "profile", None)
    return user.is_superuser or bool(profile and profile.is_active and profile.role == UserProfile.Role.SUPER_ADMIN)


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except (TypeError, ValueError):
        return None


def _decimal(value, field, default=None):
    if value in (None, ""):
        return default
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a valid number.")
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite number.")
    return result


def _money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _config_payload(config):
    return {
        "company_name": config.company_name,
        "company_address": config.company_address,
        "company_phone": config.company_phone,
        "company_email": config.company_email,
        "company_website": config.company_website,
        "tax_label": config.tax_label,
        "tax_rate": str(config.tax_rate) if config.tax_rate is not None else None,
        "manager_discount_limit_type": config.manager_discount_limit_type or None,
        "manager_discount_limit_value": str(config.manager_discount_limit_value) if config.manager_discount_limit_value is not None else None,
        "default_terms": config.default_terms,
        "default_validity_days": config.default_validity_days,
        "is_configured_for_sending": config.tax_rate is not None,
    }


def _quotation_payload(quotation):
    return {
        "id": quotation.pk,
        "quotation_no": quotation.quotation_no,
        "customer": {"id": quotation.customer_id, "name": quotation.customer.name, "phone": quotation.customer.phone, "email": quotation.customer.email, "address": quotation.customer.address},
        "product": ({"id": quotation.product_id, "name": quotation.product.name, "sku": quotation.product.sku, "image": quotation.product.image.url if quotation.product.image else None} if quotation.product_id else None),
        "item_description": quotation.item_description,
        "dimensions": quotation.dimensions,
        "quantity": str(quotation.quantity),
        "line_items": [{
            "id": item.pk, "category": item.category, "category_label": item.get_category_display(),
            "description": item.description, "dimensions": item.dimensions, "quantity": str(item.quantity),
            "unit": item.unit, "unit_price": str(item.unit_price), "line_total": str(item.line_total),
        } for item in quotation.line_items.all()],
        "subtotal": str(quotation.subtotal),
        "discount_type": quotation.discount_type,
        "discount_value": str(quotation.discount_value),
        "discount_percent": str(quotation.discount_percent),
        "discount_amount": str(quotation.discount_amount),
        "tax_rate": str(quotation.tax_rate) if quotation.tax_rate is not None else None,
        "tax_amount": str(quotation.tax_amount),
        "quoted_price": str(quotation.quoted_price),
        "advance_required": str(quotation.advance_required),
        "delivery_timeline": quotation.delivery_timeline,
        "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
        "terms": quotation.terms,
        "notes": quotation.notes,
        "status": quotation.status,
        "approval_notes": quotation.approval_notes,
        "approval_history": [{
            "action": event.action, "discount_percent": str(event.discount_percent),
            "discount_amount": str(event.discount_amount), "notes": event.notes,
            "performed_by": event.performed_by.get_full_name() or event.performed_by.username if event.performed_by else "System",
            "created_at": event.created_at.isoformat(),
        } for event in quotation.approval_history.select_related("performed_by").all()],
    }


@login_required
@require_http_methods(["GET", "POST"])
def quotation_configuration(request):
    config = QuotationConfiguration.get_solo()
    if request.method == "GET":
        return JsonResponse({"configuration": _config_payload(config), "can_configure": _founder(request.user)})
    if not _founder(request.user):
        raise PermissionDenied
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    try:
        if "tax_rate" in data:
            value = _decimal(data.get("tax_rate"), "tax_rate", None)
            if value is not None and not (Decimal("0") <= value <= Decimal("100")):
                raise ValueError("tax_rate must be between 0 and 100.")
            config.tax_rate = value
        if "manager_discount_limit_type" in data:
            limit_type = str(data.get("manager_discount_limit_type") or "").strip()
            if limit_type not in ("", "percentage", "amount"):
                raise ValueError("Choose percentage or fixed amount for the Manager Discount Limit.")
            config.manager_discount_limit_type = limit_type
        if "manager_discount_limit_value" in data:
            limit_value = _decimal(data.get("manager_discount_limit_value"), "manager_discount_limit_value", None)
            if limit_value is not None and limit_value < 0:
                raise ValueError("Manager Discount Limit cannot be negative.")
            if limit_value is not None and config.manager_discount_limit_type == "percentage" and limit_value > 100:
                raise ValueError("A percentage Manager Discount Limit cannot exceed 100%.")
            config.manager_discount_limit_value = limit_value
        for field in ("company_name", "company_address", "company_phone", "company_email", "company_website", "tax_label", "default_terms"):
            if field in data:
                setattr(config, field, str(data.get(field) or "").strip())
        if "default_validity_days" in data:
            raw = data.get("default_validity_days")
            config.default_validity_days = int(raw) if raw not in (None, "") else None
            if config.default_validity_days is not None and config.default_validity_days < 1:
                raise ValueError("default_validity_days must be at least 1.")
    except (ValueError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    config.updated_by = request.user
    config.save()
    return JsonResponse({"configuration": _config_payload(config)})


def _validated_items(raw_items):
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Add at least one itemized quotation line.")
    valid_categories = {value for value, _ in QuotationLineItem.Category.choices}
    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"Line {index + 1} is invalid.")
        category = str(raw.get("category", "")).strip()
        description = str(raw.get("description", "")).strip()
        if category not in valid_categories or not description:
            raise ValueError(f"Line {index + 1} needs a valid category and description.")
        quantity = _decimal(raw.get("quantity"), f"Line {index + 1} quantity")
        unit_price = _decimal(raw.get("unit_price"), f"Line {index + 1} unit price")
        if quantity is None or quantity <= 0 or unit_price is None or unit_price < 0:
            raise ValueError(f"Line {index + 1} quantity must be positive and unit price cannot be negative.")
        line_total = _money(quantity * unit_price)
        items.append({
            "category": category, "description": description,
            "dimensions": str(raw.get("dimensions") or "").strip(),
            "quantity": quantity, "unit": str(raw.get("unit") or "").strip(),
            "unit_price": unit_price, "line_total": line_total,
            "sort_order": index,
        })
    return items


def _save_line_items(quotation, items):
    quotation.line_items.all().delete()
    for item in items:
        QuotationLineItem.objects.create(quotation=quotation, **item)


def _calculate(quotation, config):
    subtotal = _money(sum((item.line_total for item in quotation.line_items.all()), Decimal("0")))
    discount_type = quotation.discount_type or "percentage"
    discount_value = quotation.discount_value or Decimal("0")
    if discount_value < 0:
        raise ValueError("Discount cannot be negative.")
    if discount_type == "percentage":
        if discount_value > 100:
            raise ValueError("Discount percentage must be between 0 and 100.")
        discount_percent = discount_value
        discount_amount = _money(subtotal * discount_value / Decimal("100"))
    elif discount_type == "amount":
        if discount_value > subtotal:
            raise ValueError("Fixed discount cannot exceed the quotation subtotal.")
        discount_amount = _money(discount_value)
        discount_percent = _money(discount_amount * Decimal("100") / subtotal) if subtotal else Decimal("0.00")
    else:
        raise ValueError("Choose percentage or fixed amount for the discount.")
    taxable = subtotal - discount_amount
    quotation.discount_percent = discount_percent
    quotation.discount_amount = discount_amount
    tax_rate = config.tax_rate
    if tax_rate is None:
        tax_amount = Decimal("0.00")
    else:
        tax_amount = _money(taxable * tax_rate / Decimal("100"))
    quotation.subtotal = subtotal
    quotation.discount_amount = discount_amount
    quotation.tax_rate = tax_rate
    quotation.tax_amount = tax_amount
    quotation.quoted_price = _money(taxable + tax_amount)
    return quotation


@login_required
@require_http_methods(["GET"])
def quotation_products(request):
    if not _manager(request.user):
        raise PermissionDenied
    products = Product.objects.filter(status=Product.Status.ACTIVE, customer_visible=True, category__is_active=True, category__parent__is_active=True, category__parent__is_section=True, category__is_section=False).select_related("category", "category__parent").order_by("category__parent__name", "category__name", "name")
    return JsonResponse({"products": [{"id": p.pk, "name": p.name, "sku": p.sku, "category": p.category.name, "description": p.description, "unit": p.unit, "price": str(p.customer_price), "image": p.image.url if p.image else None} for p in products]})

@login_required
@require_http_methods(["POST"])
def quotation_workflow_create(request):
    if not _manager(request.user):
        raise PermissionDenied
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    try:
        items = _validated_items(data.get("line_items"))
        customer = get_object_or_404(_customer_qs(request.user).filter(status=Customer.Status.ACTIVE), pk=data.get("customer"))
        product = get_object_or_404(Product.objects.filter(status=Product.Status.ACTIVE, customer_visible=True), pk=data["product"]) if data.get("product") not in (None, "") else None
        discount_type = str(data.get("discount_type") or "percentage")
        if discount_type not in ("percentage", "amount"):
            raise ValueError("Choose percentage or fixed amount for the discount.")
        discount = _decimal(data.get("discount_value", data.get("discount_percent", 0)), "discount_value", Decimal("0"))
        if discount is None or discount < 0:
            raise ValueError("Discount cannot be negative.")
        item_description = str(data.get("item_description") or "").strip()
        if not item_description:
            raise ValueError("Product / service description is required.")
        quantity = _decimal(data.get("quantity", 1), "quantity", Decimal("1"))
        if quantity is None or quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        advance = _decimal(data.get("advance_required", 0), "advance_required", Decimal("0"))
        if advance < 0:
            raise ValueError("Advance cannot be negative.")
        valid_until = date.fromisoformat(data["valid_until"]) if data.get("valid_until") else None
        config = QuotationConfiguration.get_solo()
        with transaction.atomic():
            quotation = Quotation.objects.create(
                customer=customer, product=product, item_description=(product.name if product else item_description),
                quantity=quantity, dimensions=str(data.get("dimensions") or "").strip(),
                discount_type=discount_type, discount_value=discount, advance_required=advance, valid_until=valid_until,
                delivery_timeline=str(data.get("delivery_timeline") or "").strip(),
                terms=str(data.get("terms") if data.get("terms") is not None else config.default_terms or ""),
                notes=str(data.get("notes") or "").strip(), status=Quotation.Status.DRAFT,
                quoted_price=Decimal("0.00"), created_by=request.user,
            )
            _save_line_items(quotation, items)
            _calculate(quotation, config)
            quotation.save()
        return JsonResponse({"quotation": _quotation_payload(quotation)}, status=201)
    except (ValueError, TypeError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@login_required
@require_http_methods(["POST"])
def quotation_workflow_update(request, pk):
    if not _manager(request.user):
        raise PermissionDenied
    quotation = get_object_or_404(_quotation_qs(request.user), pk=pk)
    if quotation.status != Quotation.Status.DRAFT:
        return JsonResponse({"detail": "Only Draft quotations can be edited. Submitted quotations are immutable."}, status=409)
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    try:
        items = _validated_items(data.get("line_items")) if "line_items" in data else None
        if "customer" in data:
            quotation.customer = get_object_or_404(_customer_qs(request.user).filter(status=Customer.Status.ACTIVE), pk=data["customer"])
        if "product" in data:
            quotation.product = get_object_or_404(Product.objects.filter(status=Product.Status.ACTIVE, customer_visible=True), pk=data["product"]) if data["product"] not in (None, "") else None
            if quotation.product:
                quotation.item_description = quotation.product.name
        for field in ("item_description", "dimensions", "delivery_timeline", "terms", "notes"):
            if field in data:
                setattr(quotation, field, str(data.get(field) or "").strip())
        if "quantity" in data:
            quotation.quantity = _decimal(data["quantity"], "quantity", Decimal("1"))
            if quotation.quantity is None or quotation.quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")
        if "discount_type" in data:
            quotation.discount_type = str(data.get("discount_type") or "percentage")
        if "discount_value" in data:
            quotation.discount_value = _decimal(data["discount_value"], "discount_value", Decimal("0"))
        elif "discount_percent" in data:
            quotation.discount_type = "percentage"
            quotation.discount_value = _decimal(data["discount_percent"], "discount_percent", Decimal("0"))
        if "advance_required" in data:
            quotation.advance_required = _decimal(data["advance_required"], "advance_required", Decimal("0"))
            if quotation.advance_required is None or quotation.advance_required < 0:
                raise ValueError("Advance cannot be negative.")
        if "valid_until" in data:
            quotation.valid_until = date.fromisoformat(data["valid_until"]) if data["valid_until"] else None
        with transaction.atomic():
            if items is not None:
                _save_line_items(quotation, items)
            _calculate(quotation, QuotationConfiguration.get_solo())
            quotation.save()
        return JsonResponse({"quotation": _quotation_payload(quotation)})
    except (ValueError, TypeError, InvalidOperation) as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


@login_required
@require_http_methods(["POST"])
def quotation_submit(request, pk):
    if not _manager(request.user):
        raise PermissionDenied
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    with transaction.atomic():
        quotation = get_object_or_404(_quotation_qs(request.user).select_for_update(), pk=pk)
        if quotation.status != Quotation.Status.DRAFT:
            return JsonResponse({"detail": "Only Draft quotations can be submitted."}, status=409)
        if not quotation.valid_until or quotation.valid_until < timezone.localdate():
            return JsonResponse({"detail": "Set a future quotation validity date before submitting."}, status=400)
        config = QuotationConfiguration.get_solo()
        if config.tax_rate is None:
            return JsonResponse({"detail": "Founder must configure the tax rate before a quotation can be sent."}, status=400)
        _calculate(quotation, config)
        limit_type = config.manager_discount_limit_type
        limit_value = config.manager_discount_limit_value
        if quotation.discount_amount > 0 and (not limit_type or limit_value is None):
            return JsonResponse({"detail": "Founder must configure the Manager Discount Limit and choose percentage or fixed amount before applying a discount."}, status=400)
        requires_approval = False
        if quotation.discount_amount > 0:
            if limit_type == "percentage":
                requires_approval = quotation.discount_percent > limit_value
            elif limit_type == "amount":
                requires_approval = quotation.discount_amount > limit_value
        quotation.company_details_snapshot = {
            "company_name": config.company_name, "company_address": config.company_address,
            "company_phone": config.company_phone, "company_email": config.company_email,
            "company_website": config.company_website, "tax_label": config.tax_label,
        }
        quotation.status = Quotation.Status.PENDING_APPROVAL if requires_approval else Quotation.Status.SENT
        if quotation.status == Quotation.Status.PENDING_APPROVAL:
            quotation.approval_requested_at = timezone.now()
            QuotationApproval.objects.create(
                quotation=quotation, action=QuotationApproval.Action.REQUESTED,
                discount_percent=quotation.discount_percent, discount_amount=quotation.discount_amount,
                performed_by=request.user,
            )
        else:
            quotation.sent_at = timezone.now()
        quotation.save()
    return JsonResponse({"quotation": _quotation_payload(quotation)})


@login_required
@require_http_methods(["POST"])
def quotation_approval_action(request, pk):
    if not _founder(request.user):
        raise PermissionDenied
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    action = data.get("action")
    if action not in ("approve", "reject"):
        return JsonResponse({"detail": "Action must be approve or reject."}, status=400)
    with transaction.atomic():
        quotation = get_object_or_404(Quotation.objects.select_for_update(), pk=pk, status=Quotation.Status.PENDING_APPROVAL)
        if quotation.valid_until and quotation.valid_until < timezone.localdate():
            quotation.status = Quotation.Status.EXPIRED
            quotation.save(update_fields=["status", "updated_at"])
            return JsonResponse({"detail": "This quotation has expired and can no longer be approved."}, status=409)
        quotation.approval_notes = str(data.get("notes") or "").strip()
        if action == "approve":
            quotation.status = Quotation.Status.SENT
            quotation.approved_by = request.user
            quotation.approved_at = timezone.now()
            quotation.sent_at = quotation.approved_at
            audit_action = QuotationApproval.Action.APPROVED
        else:
            quotation.status = Quotation.Status.REJECTED
            quotation.rejected_at = timezone.now()
            audit_action = QuotationApproval.Action.REJECTED
        quotation.save()
        QuotationApproval.objects.create(
            quotation=quotation, action=audit_action,
            discount_percent=quotation.discount_percent, discount_amount=quotation.discount_amount,
            performed_by=request.user, notes=quotation.approval_notes,
        )
    return JsonResponse({"quotation": _quotation_payload(quotation)})


@login_required
def quotation_workflow_detail(request, pk):
    quotation = get_object_or_404(_quotation_qs(request.user).select_related("customer").prefetch_related("line_items", "approval_history__performed_by"), pk=pk)
    if quotation.status in (Quotation.Status.SENT, Quotation.Status.PENDING_APPROVAL) and quotation.valid_until and quotation.valid_until < timezone.localdate():
        quotation.status = Quotation.Status.EXPIRED
        quotation.save(update_fields=["status", "updated_at"])
    return JsonResponse({"quotation": _quotation_payload(quotation)})


@login_required
def quotation_pdf(request, pk):
    quotation = get_object_or_404(_quotation_qs(request.user).select_related("customer").prefetch_related("line_items"), pk=pk)
    if quotation.status in (Quotation.Status.SENT, Quotation.Status.PENDING_APPROVAL) and quotation.valid_until and quotation.valid_until < timezone.localdate():
        quotation.status = Quotation.Status.EXPIRED
        quotation.save(update_fields=["status", "updated_at"])
        return JsonResponse({"detail": "This quotation has expired."}, status=409)
    if quotation.status not in (Quotation.Status.SENT, Quotation.Status.ACCEPTED, Quotation.Status.APPROVED):
        return JsonResponse({"detail": "A quotation PDF is available after it has been sent or accepted."}, status=409)
    return quotation_pdf_response(quotation)
