from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied
import re
import io

from .decorators import customer_required, sales_manager_required
from .forms import CustomerForm, CustomerRegistrationForm, CustomerRequestForm, CustomerInteractionForm, EnquiryForm, QuotationForm, SalesOrderForm, DesignApprovalForm
from products.models import Product
from .models import Customer, CustomerFeedback, CustomerNotification, DeliveryRecord, DesignApproval, Enquiry, OrderRequest, PaymentRecord, Quotation, SalesOrder


@login_required
def dashboard(request):
    stats = {
        "customers": Customer.objects.filter(status=Customer.Status.ACTIVE).count(),
        "new_enquiries": Enquiry.objects.filter(status=Enquiry.Status.NEW).count(),
        "quotations": Quotation.objects.exclude(status=Quotation.Status.CONVERTED).count(),
        "open_orders": SalesOrder.objects.exclude(status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]).count(),
    }
    unread_notifications = 0
    can_review_requests = False
    try:
        from accounts.models import UserProfile
        profile = getattr(request.user, "profile", None)
        can_review_requests = request.user.is_superuser or (
            profile and profile.is_active and profile.role in (
                UserProfile.Role.SUPER_ADMIN,
                UserProfile.Role.INSTITUTION_ADMIN,
                UserProfile.Role.MANAGER,
            )
        )
        if can_review_requests:
            unread_notifications = request.user.customer_notifications.filter(is_read=False).count()
    except Exception:
        pass
    return render(request, "sales/dashboard.html", {
        "title": "Customer & Sales",
        "stats": stats,
        "can_review_requests": can_review_requests,
        "unread_notifications": unread_notifications,
    })


@login_required
def customer_list(request):
    qs = Customer.objects.all()
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
    return render(request, "sales/customer_list.html", {"title": "Customers", "customers": qs, "query": query})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    orders = customer.orders.select_related("responsible_staff__user").prefetch_related("payments")[:10]
    return render(request, "sales/customer_detail.html", {
        "title": customer.name,
        "customer": customer,
        "enquiries": customer.enquiries.all()[:10],
        "quotations": customer.quotations.all()[:10],
        "orders": orders,
        "interactions": customer.interactions.select_related("created_by")[:12],
    })


@sales_manager_required
def customer_interaction_create(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerInteractionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        interaction = form.save(commit=False)
        interaction.customer = customer
        interaction.created_by = request.user
        interaction.save()
        from core.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            module="CRM",
            action=AuditLog.Action.CREATE,
            reference=customer.name,
            description=f"Customer follow-up recorded: {interaction.subject}.",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        messages.success(request, "Customer interaction saved.")
        return redirect("sales:customer_detail", pk=pk)
    return render(request, "sales/form.html", {
        "title": "Add Customer Interaction",
        "form": form,
        "back_url": "sales:customer_detail",
        "back_pk": pk,
    })


@sales_manager_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        messages.success(request, "Customer saved successfully.")
        return redirect("sales:customer_detail", pk=customer.pk)
    return render(request, "sales/form.html", {"title": "Add Customer", "form": form, "back_url": "sales:customers"})


@sales_manager_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Customer updated successfully.")
        return redirect("sales:customer_detail", pk=pk)
    return render(request, "sales/form.html", {"title": "Edit Customer", "form": form, "back_url": "sales:customer_detail", "back_pk": pk})


@login_required
def enquiry_list(request):
    qs = Enquiry.objects.select_related("customer", "assigned_to")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(Q(enquiry_no__icontains=query) | Q(customer__name__icontains=query) | Q(product_type__icontains=query))
    return render(request, "sales/enquiry_list.html", {"title": "Customer Enquiries", "enquiries": qs, "query": query})


@sales_manager_required
def enquiry_create(request):
    form = EnquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.created_by = request.user
        enquiry.save()
        messages.success(request, f"Enquiry {enquiry.enquiry_no} created.")
        return redirect("sales:enquiries")
    return render(request, "sales/form.html", {"title": "New Customer Enquiry", "form": form, "back_url": "sales:enquiries"})


@sales_manager_required
def enquiry_edit(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    form = EnquiryForm(request.POST or None, instance=enquiry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Enquiry updated.")
        return redirect("sales:enquiries")
    return render(request, "sales/form.html", {"title": "Edit Enquiry", "form": form, "back_url": "sales:enquiries"})


@login_required
def quotation_list(request):
    qs = Quotation.objects.select_related("customer", "enquiry", "created_by")
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(Q(quotation_no__icontains=query) | Q(customer__name__icontains=query) | Q(item_description__icontains=query))
    return render(request, "sales/quotation_list.html", {"title": "Quotations", "quotations": qs, "query": query})


@sales_manager_required
def quotation_create(request):
    initial = {}
    request_id = request.GET.get("request") or request.GET.get("order_request")
    if request_id:
        order_request = OrderRequest.objects.select_related("customer", "product").filter(
            pk=request_id
        ).first()
        if order_request:
            initial = {
                "customer": order_request.customer_id,
                "order_request": order_request.pk,
                "item_description": order_request.product.name if order_request.product_id else order_request.product_name,
                "quantity": order_request.quantity,
                "notes": order_request.requirement,
            }
    form = QuotationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        quotation = form.save(commit=False)
        quotation.created_by = request.user
        quotation.save()
        if quotation.order_request_id:
            OrderRequest.objects.filter(pk=quotation.order_request_id).update(
                status=OrderRequest.Status.QUOTATION,
                updated_at=timezone.now(),
            )
        if quotation.status == Quotation.Status.SENT and quotation.customer.user_id:
            CustomerNotification.objects.create(
                user=quotation.customer.user,
                notification_type=CustomerNotification.NotificationType.QUOTATION,
                title=f"Quotation {quotation.quotation_no} is ready",
                message="A quotation is ready for your review.",
                url=f"/sales/portal/quotations/{quotation.pk}/",
            )
        messages.success(request, f"Quotation {quotation.quotation_no} created.")
        return redirect("sales:quotation_detail", pk=quotation.pk)
    return render(request, "sales/quotation_form.html", {
        "title": "New Quotation",
        "form": form,
        "back_url": "sales:quotations",
        "quotation": None,
    })


@login_required
def quotation_pdf(request, pk):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    quotation = get_object_or_404(
        Quotation.objects.select_related("customer", "created_by", "order_request"),
        pk=pk,
    )

    # Customers can only download their own quotation.
    customer = _customer_for_user(request.user)
    if customer and quotation.customer_id != customer.id:
        raise PermissionDenied

    if not customer:
        try:
            from accounts.models import UserProfile
            profile = getattr(request.user, "profile", None)
            allowed = request.user.is_superuser or (
                profile and profile.is_active and profile.role in (
                    UserProfile.Role.SUPER_ADMIN,
                    UserProfile.Role.INSTITUTION_ADMIN,
                    UserProfile.Role.MANAGER,
                )
            )
        except Exception:
            allowed = request.user.is_superuser
        if not allowed:
            raise PermissionDenied

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=17*mm, bottomMargin=17*mm,
        title=f"Quotation {quotation.quotation_no}",
        author="SADACO Management System",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "QTitle", parent=styles["Title"], fontSize=24, leading=28,
        textColor=colors.HexColor("#0f172a"), spaceAfter=4,
    )
    sub = ParagraphStyle(
        "QSub", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#64748b"), spaceAfter=14,
    )
    section = ParagraphStyle(
        "QSection", parent=styles["Heading2"], fontSize=12,
        textColor=colors.HexColor("#172554"), spaceBefore=12, spaceAfter=7,
    )
    small = ParagraphStyle(
        "QSmall", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#475569"), leading=11,
    )

    story = [
        Paragraph("SADACO", title),
        Paragraph("Management System · Customer Quotation", sub),
    ]

    header = Table([
        [Paragraph("<b>QUOTATION</b>", styles["Normal"]), Paragraph(
            f"<b>{quotation.quotation_no}</b><br/>Date: {quotation.created_at.strftime('%d %b %Y')}",
            styles["Normal"]
        )],
    ], colWidths=[82*mm, 82*mm])
    header.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#eff6ff")),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor("#172554")),
        ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#bfdbfe")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
    ]))
    story += [header, Spacer(1, 8)]

    customer_data = [
        ["Customer", quotation.customer.name, "Valid Until", str(quotation.valid_until or "—")],
        ["Phone", quotation.customer.phone or "—", "Delivery", quotation.delivery_timeline or "—"],
        ["Email", quotation.customer.email or "—", "Quantity", str(quotation.quantity)],
    ]
    ct=Table(customer_data,colWidths=[24*mm,58*mm,25*mm,57*mm])
    ct.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor("#334155")),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#e2e8f0")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f8fafc")),
        ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#f8fafc")),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
    ]))
    story += [ct]

    story.append(Paragraph("Cost & Commercial Details", section))
    rows=[
        ["Description", "Amount (₹)"],
        ["Material", f"{quotation.material_cost:,.2f}"],
        ["Labour", f"{quotation.labour_cost:,.2f}"],
        ["Machine / Production", f"{quotation.machine_cost:,.2f}"],
        ["Finishing", f"{quotation.finishing_cost:,.2f}"],
        ["Packaging", f"{quotation.packaging_cost:,.2f}"],
        ["Delivery", f"{quotation.delivery_cost:,.2f}"],
        ["Total Cost", f"{quotation.cost_total:,.2f}"],
        ["Quoted Price", f"{quotation.quoted_price:,.2f}"],
        ["Advance Required", f"{quotation.advance_required:,.2f}"],
    ]
    cost=Table(rows,colWidths=[120*mm,44*mm],repeatRows=1)
    cost.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#172554")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ALIGN",(1,1),(1,-1),"RIGHT"),("FONTNAME",(0,7),(-1,9),"Helvetica-Bold"),
        ("BACKGROUND",(0,7),(-1,9),colors.HexColor("#eff6ff")),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dbe3ed")),
        ("FONTSIZE",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
    ]))
    story += [cost]

    story.append(Paragraph("Item / Requirement", section))
    story.append(Paragraph(
        f"<b>{quotation.item_description}</b><br/>Quantity: {quotation.quantity}",
        small
    ))
    if quotation.notes:
        story += [Spacer(1,5), Paragraph(f"<b>Notes:</b> {quotation.notes}", small)]

    story += [
        Spacer(1,16),
        Paragraph(
            "This quotation is subject to the validity date and final confirmation by SADACO. "
            "The customer may approve or reject the quotation from the SADACO Customer Portal.",
            small,
        ),
    ]
    doc.build(story)
    buffer.seek(0)
    from django.http import FileResponse
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"{quotation.quotation_no}.pdf",
        content_type="application/pdf",
    )


@login_required
def quotation_detail(request, pk):
    quotation = get_object_or_404(Quotation.objects.select_related("customer", "enquiry", "created_by"), pk=pk)
    return render(request, "sales/quotation_detail.html", {
        "title": quotation.quotation_no,
        "quotation": quotation,
        "cost_items": [
            ("Material", quotation.material_cost),
            ("Labour", quotation.labour_cost),
            ("Machine / Production", quotation.machine_cost),
            ("Finishing", quotation.finishing_cost),
            ("Packaging", quotation.packaging_cost),
            ("Delivery", quotation.delivery_cost),
        ],
    })


@sales_manager_required
def quotation_edit(request, pk):
    quotation = get_object_or_404(Quotation, pk=pk)
    old_status = quotation.status
    form = QuotationForm(request.POST or None, instance=quotation)
    if request.method == "POST" and form.is_valid():
        quotation = form.save()
        if quotation.status == Quotation.Status.SENT and old_status != Quotation.Status.SENT and quotation.customer.user_id:
            CustomerNotification.objects.create(
                user=quotation.customer.user,
                notification_type=CustomerNotification.NotificationType.QUOTATION,
                title=f"Quotation {quotation.quotation_no} is ready",
                message="A quotation is ready for your review.",
                url=f"/sales/portal/quotations/{quotation.pk}/",
            )
        messages.success(request, "Quotation updated.")
        return redirect("sales:quotation_detail", pk=pk)
    return render(request, "sales/quotation_form.html", {
        "title": "Edit Quotation",
        "form": form,
        "back_url": "sales:quotation_detail",
        "back_pk": pk,
        "quotation": quotation,
    })


@login_required
def order_list(request):
    qs = SalesOrder.objects.select_related("customer", "quotation", "responsible_staff__user")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        qs = qs.filter(
            Q(order_no__icontains=query) |
            Q(customer__name__icontains=query) |
            Q(item_description__icontains=query)
        )
    if status:
        qs = qs.filter(status=status)
    stats = {
        "confirmed": SalesOrder.objects.filter(status=SalesOrder.Status.CONFIRMED).count(),
        "design": SalesOrder.objects.filter(status=SalesOrder.Status.DESIGN_PENDING).count(),
        "production": SalesOrder.objects.filter(status__in=[
            SalesOrder.Status.PRODUCTION_PENDING, SalesOrder.Status.IN_PRODUCTION
        ]).count(),
        "ready": SalesOrder.objects.filter(status=SalesOrder.Status.READY).count(),
    }
    return render(request, "sales/order_list.html", {
        "title": "Orders",
        "orders": qs,
        "query": query,
        "selected_status": status,
        "status_choices": SalesOrder.Status.choices,
        "stats": stats,
    })


@sales_manager_required
def order_create(request):
    initial = {}
    quotation_id = request.GET.get("quotation")
    if quotation_id:
        quotation = Quotation.objects.filter(pk=quotation_id).first()
        if quotation:
            initial = {"customer": quotation.customer_id, "quotation": quotation.pk, "item_description": quotation.item_description, "quantity": quotation.quantity, "confirmed_price": quotation.quoted_price, "advance_required": quotation.advance_required}
    form = SalesOrderForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        if order.quotation_id and order.quotation.status != Quotation.Status.APPROVED:
            messages.error(request, "Only a customer-approved quotation can be converted into an order.")
            return render(request, "sales/form.html", {"title": "Confirm Order", "form": form, "back_url": "sales:orders"})
        order.created_by = request.user
        order.save()
        if order.quotation_id:
            Quotation.objects.filter(pk=order.quotation_id).update(status=Quotation.Status.CONVERTED)
            if order.quotation.enquiry_id:
                Enquiry.objects.filter(pk=order.quotation.enquiry_id).update(status=Enquiry.Status.CONVERTED)
            if order.quotation.order_request_id:
                OrderRequest.objects.filter(pk=order.quotation.order_request_id).update(
                    status=OrderRequest.Status.CONFIRMED, updated_at=timezone.now()
                )
        DeliveryRecord.objects.get_or_create(
            order=order, defaults={"address": order.customer.address}
        )
        if order.customer.user_id:
            CustomerNotification.objects.create(
                user=order.customer.user,
                notification_type=CustomerNotification.NotificationType.ORDER,
                title=f"Order {order.order_no} confirmed",
                message="Your quotation has been converted into a confirmed SADACO order.",
                url=f"/sales/portal/orders/{order.pk}/",
            )
        messages.success(request, f"Order {order.order_no} confirmed.")
        return redirect("sales:order_detail", pk=order.pk)
    return render(request, "sales/form.html", {"title": "Confirm Order", "form": form, "back_url": "sales:orders"})


@login_required
def order_pdf(request, pk):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from django.http import FileResponse

    order = get_object_or_404(
        SalesOrder.objects.select_related("customer", "quotation", "responsible_staff__user"),
        pk=pk,
    )
    customer = _customer_for_user(request.user)
    if customer and order.customer_id != customer.id:
        raise PermissionDenied
    if not customer:
        try:
            from accounts.models import UserProfile
            profile = getattr(request.user, "profile", None)
            allowed = request.user.is_superuser or (
                profile and profile.is_active and profile.role in (
                    UserProfile.Role.SUPER_ADMIN,
                    UserProfile.Role.INSTITUTION_ADMIN,
                    UserProfile.Role.MANAGER,
                )
            )
        except Exception:
            allowed = request.user.is_superuser
        if not allowed:
            raise PermissionDenied

    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=17*mm,bottomMargin=17*mm,
                          title=f"Order {order.order_no}",author="SADACO Management System")
    styles=getSampleStyleSheet()
    title=ParagraphStyle("OT",parent=styles["Title"],fontSize=23,textColor=colors.HexColor("#0f172a"))
    small=ParagraphStyle("OS",parent=styles["Normal"],fontSize=8,textColor=colors.HexColor("#475569"),leading=11)
    story=[Paragraph("SADACO",title),Paragraph("Management System · Order Confirmation",small),Spacer(1,10)]
    head=Table([[Paragraph("<b>CONFIRMED ORDER</b>",styles["Normal"]),
                 Paragraph(f"<b>{order.order_no}</b><br/>Date: {order.created_at.strftime('%d %b %Y')}",styles["Normal"])]],
               colWidths=[82*mm,82*mm])
    head.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#eff6ff")),
                              ("BOX",(0,0),(-1,-1),.5,colors.HexColor("#bfdbfe")),
                              ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor("#172554")),
                              ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                              ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    story += [head,Spacer(1,9)]
    info=Table([
        ["Customer",order.customer.name,"Phone",order.customer.phone or "—"],
        ["Item",order.item_description,"Quantity",str(order.quantity)],
        ["Confirmed Price",f"₹ {order.confirmed_price:,.2f}","Advance Required",f"₹ {order.advance_required:,.2f}"],
        ["Deadline",str(order.deadline or "—"),"Delivery Date",str(order.delivery_date or "—")],
        ["Status",order.get_status_display(),"Responsible",order.responsible_staff.user.get_full_name() if order.responsible_staff else "Not assigned"],
    ],colWidths=[30*mm,52*mm,30*mm,52*mm])
    info.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,colors.HexColor("#dbe3ed")),
                              ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f8fafc")),
                              ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#f8fafc")),
                              ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
                              ("FONTSIZE",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story += [info,Spacer(1,12)]
    if order.notes: story += [Paragraph("<b>Notes</b>",styles["Heading2"]),Paragraph(order.notes,small),Spacer(1,10)]
    payments=list(order.payments.all())
    received=sum((p.amount for p in payments if p.status in (PaymentRecord.Status.RECEIVED,PaymentRecord.Status.VERIFIED)),0)
    story += [Paragraph("<b>Payment Summary</b>",styles["Heading2"]),
              Paragraph(f"Received / Verified: ₹ {received:,.2f}<br/>Balance: ₹ {order.confirmed_price-received:,.2f}",small)]
    delivery=getattr(order,"delivery",None)
    if delivery:
        story += [Spacer(1,10),Paragraph("<b>Delivery / Installation</b>",styles["Heading2"]),
                  Paragraph(f"Status: {delivery.get_status_display()}<br/>Delivery date: {delivery.delivery_date or '—'}<br/>Installation: {'Required' if delivery.installation_required else 'Not required'}",small)]
    doc.build(story); buffer.seek(0)
    return FileResponse(buffer,as_attachment=True,filename=f"{order.order_no}.pdf",content_type="application/pdf")


@login_required
def order_detail(request, pk):
    order = get_object_or_404(SalesOrder.objects.select_related("customer", "quotation", "responsible_staff__user", "created_by"), pk=pk)
    payment_total = sum((p.amount for p in order.payments.all() if p.status in (
        PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED
    )), 0)
    balance = order.confirmed_price - payment_total
    return render(request, "sales/order_detail.html", {
        "title": order.order_no,
        "order": order,
        "payment_total": payment_total,
        "balance": balance,
        "status_choices": SalesOrder.Status.choices,
    })


@sales_manager_required
def order_edit(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    old_status = order.status
    form = SalesOrderForm(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid():
        order = form.save()
        if order.customer.user_id and order.status != old_status:
            CustomerNotification.objects.create(
                user=order.customer.user,
                notification_type=CustomerNotification.NotificationType.ORDER,
                title=f"Order {order.order_no} updated",
                message=f"Your order status is now: {order.get_status_display()}.",
                url=f"/sales/portal/orders/{order.pk}/",
            )
        messages.success(request, "Order updated.")
        return redirect("sales:order_detail", pk=pk)
    return render(request, "sales/order_form.html", {
        "title": "Edit Order",
        "form": form,
        "order": order,
        "back_url": "sales:order_detail",
        "back_pk": pk,
    })


def _manager_users():
    from accounts.models import UserProfile
    return User.objects.filter(
        profile__role__in=[
            UserProfile.Role.SUPER_ADMIN,
            UserProfile.Role.INSTITUTION_ADMIN,
            UserProfile.Role.MANAGER,
        ],
        profile__is_active=True,
        is_active=True,
    ).distinct()


def _customer_for_user(user):
    return getattr(user, "customer_profile", None)


def customer_register(request):
    if request.user.is_authenticated and hasattr(request.user, "customer_profile"):
        return redirect("sales:portal_dashboard")

    form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"].strip()
        phone = form.cleaned_data["phone"].strip()
        email = form.cleaned_data["email"].strip()
        base_username = "c_" + re.sub(r"[^0-9A-Za-z]", "", phone)
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}_{suffix}"

        user = User(
            username=username,
            email=email,
            first_name=name,
        )
        user.set_password(form.cleaned_data["password"])
        user.save()
        customer = Customer.objects.filter(phone=phone, user__isnull=True).first()
        if customer:
            customer.user = user
            customer.name = name or customer.name
            customer.email = email or customer.email
            customer.save(update_fields=["user", "name", "email", "updated_at"])
        else:
            customer = Customer.objects.create(
                user=user, name=name, phone=phone, email=email
            )
        messages.success(request, "Your SADACO customer account has been created. Please sign in using your mobile number and password.")
        return redirect("accounts:login")

    return render(request, "sales/portal_register.html", {"title": "Create Customer Account", "form": form})


def customer_login(request):
    """Compatibility entry point: Customer login now uses the unified SADACO login page."""
    return redirect("accounts:login")


@customer_required
@customer_required
@customer_required
def portal_product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("category"),
        pk=pk,
        status=Product.Status.ACTIVE,
        customer_visible=True,
    )
    return render(request, "sales/portal_product_detail.html", {
        "title": product.name,
        "product": product,
    })


def portal_products(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("category").filter(
        status=Product.Status.ACTIVE,
        customer_visible=True,
    )
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(category__name__icontains=query)
        )
    return render(request, "sales/portal_products.html", {
        "title": "Products",
        "products": products,
        "query": query,
    })


@customer_required
def portal_notifications(request):
    notifications = request.user.customer_notifications.all()
    return render(request, "sales/portal_notifications.html", {
        "title": "Notifications",
        "notifications": notifications,
    })


@customer_required
def portal_notification_read(request, pk):
    notification = get_object_or_404(
        request.user.customer_notifications.all(), pk=pk
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.url:
        return redirect(notification.url)
    return redirect("sales:portal_notifications")


def portal_dashboard(request):
    customer = _customer_for_user(request.user)
    return render(request, "sales/portal_dashboard.html", {
        "title": "Customer Portal",
        "customer": customer,
        "requests": customer.order_requests.all()[:6],
        "quotations": customer.quotations.all()[:6],
        "orders": customer.orders.all()[:6],
        "notifications": request.user.customer_notifications.filter(is_read=False)[:6],
    })


@customer_required
def portal_request_create(request):
    customer = _customer_for_user(request.user)
    selected_product = request.GET.get("product")
    initial = {}
    if selected_product and request.method == "GET":
        try:
            product = Product.objects.get(
                pk=selected_product,
                status=Product.Status.ACTIVE,
                customer_visible=True,
            )
            initial = {"product": product.pk, "product_name": product.name}
        except (Product.DoesNotExist, ValueError):
            initial = {}
    form = CustomerRequestForm(
        request.POST or None,
        request.FILES or None,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.customer = customer
        obj.save()

        for manager in _manager_users():
            CustomerNotification.objects.create(
                user=manager,
                notification_type=CustomerNotification.NotificationType.REQUEST,
                title="New customer request",
                message=f"{customer.name} submitted {obj.request_no}.",
                url=f"/sales/requests/{obj.pk}/",
            )

        messages.success(request, "Your request has been submitted. Our manager will contact you.")
        return redirect("sales:portal_requests")
    return render(request, "sales/portal_form.html", {"title": "New Request", "form": form})


@customer_required
def portal_quotations(request):
    customer = _customer_for_user(request.user)
    return render(request, "sales/portal_quotations.html", {
        "title": "My Quotations",
        "quotations": customer.quotations.all(),
    })


@customer_required
def portal_quotation_detail(request, pk):
    customer = _customer_for_user(request.user)
    quotation = get_object_or_404(
        Quotation.objects.prefetch_related("designs"), pk=pk, customer=customer
    )
    latest_design = quotation.designs.first()
    return render(request, "sales/portal_quotation_detail.html", {
        "title": quotation.quotation_no,
        "quotation": quotation,
        "latest_design": latest_design,
    })


@customer_required
def portal_quotation_response(request, pk):
    customer = _customer_for_user(request.user)
    quotation = get_object_or_404(Quotation, pk=pk, customer=customer)
    if request.method != "POST":
        return redirect("sales:portal_quotation_detail", pk=pk)
    if quotation.status != Quotation.Status.SENT:
        messages.error(request, "This quotation is not currently awaiting your response.")
        return redirect("sales:portal_quotation_detail", pk=pk)
    decision = request.POST.get("decision")
    if decision not in ("approved", "rejected"):
        messages.error(request, "Invalid quotation response.")
        return redirect("sales:portal_quotation_detail", pk=pk)
    quotation.status = Quotation.Status.APPROVED if decision == "approved" else Quotation.Status.REJECTED
    quotation.save(update_fields=["status", "updated_at"])
    for manager in _manager_users():
        CustomerNotification.objects.create(
            user=manager,
            notification_type=CustomerNotification.NotificationType.QUOTATION,
            title=f"Quotation {quotation.quotation_no} response",
            message=f"{customer.name} has {quotation.get_status_display().lower()} the quotation.",
            url=f"/sales/quotations/{quotation.pk}/",
        )
    try:
        from accounts.notification_service import notify_roles
        notify_roles(
            title=f"Quotation {quotation.quotation_no} response",
            message=f"{customer.name} has {quotation.get_status_display().lower()} the quotation.",
            notification_type="order",
            priority="high",
            url=f"/sales/quotations/{quotation.pk}/",
        )
    except Exception:
        pass
    messages.success(request, "Your quotation response has been recorded.")
    return redirect("sales:portal_quotation_detail", pk=pk)


@customer_required
def portal_design_response(request, pk):
    customer = _customer_for_user(request.user)
    design = get_object_or_404(DesignApproval.objects.select_related("quotation"), pk=pk, quotation__customer=customer)
    if request.method != "POST":
        return redirect("sales:portal_quotation_detail", pk=design.quotation_id)
    decision = request.POST.get("decision")
    if decision == "approved":
        design.status = DesignApproval.Status.APPROVED
    elif decision == "revision":
        design.status = DesignApproval.Status.REVISION
    else:
        messages.error(request, "Invalid design response.")
        return redirect("sales:portal_quotation_detail", pk=design.quotation_id)
    design.customer_notes = request.POST.get("customer_notes", "").strip()
    design.responded_at = timezone.now()
    design.save(update_fields=["status", "customer_notes", "responded_at", "updated_at"])
    if design.status == DesignApproval.Status.APPROVED:
        SalesOrder.objects.filter(quotation_id=design.quotation_id).exclude(
            status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]
        ).update(status=SalesOrder.Status.PRODUCTION_PENDING, updated_at=timezone.now())
    elif design.status == DesignApproval.Status.REVISION:
        SalesOrder.objects.filter(quotation_id=design.quotation_id).exclude(
            status__in=[SalesOrder.Status.DELIVERED, SalesOrder.Status.CANCELLED]
        ).update(status=SalesOrder.Status.DESIGN_PENDING, updated_at=timezone.now())
    for manager in _manager_users():
        CustomerNotification.objects.create(
            user=manager,
            notification_type=CustomerNotification.NotificationType.STATUS,
            title=f"Design response for {design.quotation.quotation_no}",
            message=f"{customer.name} responded: {design.get_status_display()}.",
            url=f"/sales/quotations/{design.quotation_id}/",
        )
    messages.success(request, "Your design response has been recorded.")
    return redirect("sales:portal_quotation_detail", pk=design.quotation_id)


@customer_required
def portal_requests(request):
    customer = _customer_for_user(request.user)
    return render(request, "sales/portal_requests.html", {
        "title": "My Requests",
        "requests": customer.order_requests.all(),
    })


@customer_required
def portal_request_detail(request, pk):
    customer = _customer_for_user(request.user)
    obj = get_object_or_404(OrderRequest, pk=pk, customer=customer)
    return render(request, "sales/portal_request_detail.html", {"title": obj.request_no, "request_obj": obj})


@login_required
def manager_requests(request):
    from accounts.models import UserProfile
    if request.user.is_superuser:
        pass
    elif not hasattr(request.user, "profile") or request.user.profile.role not in (
        UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER
    ):
        raise PermissionDenied
    requests = OrderRequest.objects.select_related("customer", "product", "assigned_to")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        requests = requests.filter(
            Q(request_no__icontains=query) |
            Q(customer__name__icontains=query) |
            Q(customer__phone__icontains=query) |
            Q(product__name__icontains=query) |
            Q(product_name__icontains=query)
        )
    if status:
        requests = requests.filter(status=status)
    stats = {
        "new": OrderRequest.objects.filter(status=OrderRequest.Status.NEW).count(),
        "reviewing": OrderRequest.objects.filter(status=OrderRequest.Status.REVIEWING).count(),
        "contacted": OrderRequest.objects.filter(status=OrderRequest.Status.CONTACTED).count(),
        "quotation": OrderRequest.objects.filter(status=OrderRequest.Status.QUOTATION).count(),
    }
    return render(request, "sales/manager_requests.html", {
        "title": "Customer Requests",
        "requests": requests,
        "query": query,
        "selected_status": status,
        "status_choices": OrderRequest.Status.choices,
        "stats": stats,
        "unread_notifications": request.user.customer_notifications.filter(is_read=False)[:10],
    })


@sales_manager_required
def manager_request_review(request, pk):
    obj = get_object_or_404(OrderRequest.objects.select_related("customer", "product"), pk=pk)
    if request.method == "POST":
        status = request.POST.get("status", OrderRequest.Status.REVIEWING)
        allowed = {x[0] for x in OrderRequest.Status.choices}
        if status not in allowed:
            status = OrderRequest.Status.REVIEWING
        obj.status = status
        obj.manager_notes = request.POST.get("manager_notes", "").strip()
        obj.assigned_to = request.user
        obj.save(update_fields=["status", "manager_notes", "assigned_to", "updated_at"])
        if obj.customer.user_id:
            CustomerNotification.objects.create(
                user=obj.customer.user,
                notification_type=CustomerNotification.NotificationType.STATUS,
                title=f"Request {obj.request_no} updated",
                message=f"Your request is now: {obj.get_status_display()}.",
                url=f"/sales/portal/requests/{obj.pk}/",
            )
        messages.success(request, "Customer request updated.")
        return redirect("sales:manager_requests")
    return render(request, "sales/manager_request_detail.html", {
        "title": obj.request_no,
        "request_obj": obj,
        "request_status_choices": OrderRequest.Status.choices,
        "customer_has_account": bool(obj.customer.user_id),
        "existing_quotation": obj.quotations.order_by("-created_at").first(),
    })


@login_required
def manager_notifications(request):
    from accounts.models import UserProfile
    if not request.user.is_superuser and (
        not hasattr(request.user, "profile") or request.user.profile.role not in (
            UserProfile.Role.SUPER_ADMIN, UserProfile.Role.INSTITUTION_ADMIN, UserProfile.Role.MANAGER
        )
    ):
        raise PermissionDenied
    notifications = request.user.customer_notifications.all()
    request.user.customer_notifications.filter(is_read=False).update(is_read=True)
    return render(request, "sales/manager_notifications.html", {
        "title": "Notifications", "notifications": notifications
    })


@sales_manager_required
@transaction.atomic
def confirm_quotation_order(request, pk):
    quotation = get_object_or_404(
        Quotation.objects.select_related("customer", "enquiry"), pk=pk
    )
    if request.method != "POST":
        return redirect("sales:quotation_detail", pk=pk)
    if quotation.status != Quotation.Status.APPROVED:
        messages.error(request, "Only customer-approved quotations can be confirmed as orders.")
        return redirect("sales:quotation_detail", pk=pk)
    latest_design = quotation.designs.first()
    if latest_design and latest_design.status != DesignApproval.Status.APPROVED:
        messages.error(request, "Customer design approval is required before order confirmation.")
        return redirect("sales:quotation_detail", pk=pk)
    existing = quotation.orders.first()
    if existing:
        messages.info(request, f"Order {existing.order_no} already exists for this quotation.")
        return redirect("sales:order_detail", pk=existing.pk)

    order_status = (
        SalesOrder.Status.PRODUCTION_PENDING
        if latest_design and latest_design.status == DesignApproval.Status.APPROVED
        else SalesOrder.Status.CONFIRMED
    )
    order = SalesOrder.objects.create(
        customer=quotation.customer,
        quotation=quotation,
        item_description=quotation.item_description,
        quantity=quotation.quantity,
        confirmed_price=quotation.quoted_price,
        advance_required=quotation.advance_required,
        status=order_status,
        created_by=request.user,
    )
    quotation.status = Quotation.Status.CONVERTED
    quotation.save(update_fields=["status", "updated_at"])
    if quotation.enquiry_id:
        Enquiry.objects.filter(pk=quotation.enquiry_id).update(status=Enquiry.Status.CONVERTED)
    if quotation.order_request_id:
        OrderRequest.objects.filter(pk=quotation.order_request_id).update(
            status=OrderRequest.Status.CONFIRMED,
            updated_at=timezone.now(),
        )
    DeliveryRecord.objects.get_or_create(order=order, defaults={"address": quotation.customer.address})
    if quotation.customer.user_id:
        CustomerNotification.objects.create(
            user=quotation.customer.user,
            notification_type=CustomerNotification.NotificationType.ORDER,
            title=f"Order {order.order_no} confirmed",
            message="Your order has been confirmed by SADACO.",
            url=f"/sales/portal/orders/{order.pk}/",
        )
    messages.success(request, f"Order {order.order_no} confirmed.")
    return redirect("sales:order_detail", pk=order.pk)


@sales_manager_required
def create_design(request, pk):
    quotation = get_object_or_404(Quotation.objects.select_related("customer"), pk=pk)
    latest = quotation.designs.first()
    version = (latest.version + 1) if latest else 1
    form = DesignApprovalForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        design = form.save(commit=False)
        design.quotation = quotation
        design.version = version
        design.status = DesignApproval.Status.SENT
        design.sent_at = timezone.now()
        design.created_by = request.user
        design.save()
        if quotation.customer.user_id:
            CustomerNotification.objects.create(
                user=quotation.customer.user,
                notification_type=CustomerNotification.NotificationType.STATUS,
                title=f"Design v{design.version} ready",
                message=f"Design version {design.version} for {quotation.quotation_no} is ready for your approval.",
                url=f"/sales/portal/quotations/{quotation.pk}/",
            )
        messages.success(request, f"Design version {design.version} sent to customer.")
        return redirect("sales:design_history", pk=pk)
    return render(request, "sales/design_form.html", {
        "title": f"Send Design · {quotation.quotation_no}",
        "quotation": quotation,
        "form": form,
        "latest_design": latest,
        "next_version": version,
    })


@sales_manager_required
def design_history(request, pk):
    quotation = get_object_or_404(Quotation.objects.select_related("customer"), pk=pk)
    designs = quotation.designs.select_related("created_by").all()
    return render(request, "sales/design_history.html", {
        "title": f"Designs · {quotation.quotation_no}",
        "quotation": quotation,
        "designs": designs,
    })


@sales_manager_required
def payment_create(request, pk):
    # Backward-compatible entry point. Payment entry now lives in Finance & Accounts.
    return redirect("finance:payment_create", pk=pk)


@customer_required
def portal_order_detail(request, pk):
    customer = _customer_for_user(request.user)
    order = get_object_or_404(
        SalesOrder.objects.select_related("quotation").prefetch_related("payments"),
        pk=pk, customer=customer
    )
    return render(request, "sales/portal_order_detail.html", {
        "title": order.order_no,
        "order": order,
        "delivery": getattr(order, "delivery", None),
    })


@customer_required
def portal_orders(request):
    customer = _customer_for_user(request.user)
    return render(request, "sales/portal_orders.html", {
        "title": "My Orders",
        "orders": customer.orders.all(),
    })


@customer_required
def portal_feedback(request, pk):
    customer = _customer_for_user(request.user)
    order = get_object_or_404(SalesOrder, pk=pk, customer=customer, status=SalesOrder.Status.DELIVERED)
    if request.method == "POST":
        rating = request.POST.get("rating") or None
        if rating and not (1 <= int(rating) <= 5):
            messages.error(request, "Rating must be between 1 and 5.")
            return redirect("sales:portal_feedback", pk=pk)
        CustomerFeedback.objects.update_or_create(
            order=order,
            defaults={"rating": rating, "comment": request.POST.get("comment", "").strip()},
        )
        messages.success(request, "Thank you for your feedback.")
        return redirect("sales:portal_order_detail", pk=pk)
    return render(request, "sales/portal_feedback.html", {"title": "Order Feedback", "order": order})


@sales_manager_required
def delivery_update(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    delivery, _ = DeliveryRecord.objects.get_or_create(
        order=order, defaults={"address": order.customer.address}
    )
    if request.method == "POST":
        delivery.delivery_date = request.POST.get("delivery_date") or None
        delivery.address = request.POST.get("address", "").strip()
        delivery.transport = request.POST.get("transport", "").strip()
        delivery.responsible_person = request.POST.get("responsible_person", "").strip()
        delivery.installation_required = request.POST.get("installation_required") == "on"
        delivery.installation_date = request.POST.get("installation_date") or None
        delivery.status = request.POST.get("status", DeliveryRecord.Status.PENDING)
        delivery.acknowledgement = request.POST.get("acknowledgement", "").strip()
        delivery.completion_notes = request.POST.get("completion_notes", "").strip()
        delivery.save()
        if delivery.status in (DeliveryRecord.Status.DELIVERED, DeliveryRecord.Status.INSTALLED):
            order.status = SalesOrder.Status.DELIVERED
            order.save(update_fields=["status", "updated_at"])
        if order.customer.user_id:
            CustomerNotification.objects.create(
                user=order.customer.user,
                notification_type=CustomerNotification.NotificationType.STATUS,
                title=f"Delivery update for {order.order_no}",
                message=f"Delivery status: {delivery.get_status_display()}.",
                url=f"/sales/portal/orders/{order.pk}/",
            )
        messages.success(request, "Delivery information updated.")
        return redirect("sales:order_detail", pk=pk)
    return render(request, "sales/delivery_form.html", {
        "title": "Delivery / Installation",
        "order": order,
        "delivery": delivery,
        "delivery_statuses": DeliveryRecord.Status.choices,
    })
