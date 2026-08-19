import csv
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum, Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.http import FileResponse
import io
from accounts.decorators import role_required

from products.models import Product, StockTransaction
from sales.models import Customer, Enquiry, Quotation, SalesOrder, PaymentRecord
from staff.models import StaffProfile, StaffAttendance, StaffTask
from purchase.models import PurchaseOrder, Supplier
from finance.models import Expense
from sales.models import DeliveryRecord
from marketing.models import Campaign, MarketingLead


def _date_range(request):
    today = timezone.localdate()
    default_start = today - timedelta(days=29)
    raw_start = request.GET.get("start", "")
    raw_end = request.GET.get("end", "")
    try:
        start = date.fromisoformat(raw_start) if raw_start else default_start
    except ValueError:
        start = default_start
    try:
        end = date.fromisoformat(raw_end) if raw_end else today
    except ValueError:
        end = today
    if start > end:
        start, end = end, start
    return start, end


def _money(value):
    return value or Decimal("0")


@login_required
@role_required("super_admin", "institution_admin", "manager")
def dashboard(request):
    start, end = _date_range(request)

    orders = SalesOrder.objects.filter(created_at__date__range=(start, end))
    enquiries = Enquiry.objects.filter(created_at__date__range=(start, end))
    quotations = Quotation.objects.filter(created_at__date__range=(start, end))
    payments = PaymentRecord.objects.filter(
        created_at__date__range=(start, end),
        status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED],
    )
    stock = StockTransaction.objects.filter(created_at__date__range=(start, end))

    order_revenue = _money(
        orders.exclude(status=SalesOrder.Status.CANCELLED).aggregate(total=Sum("confirmed_price"))["total"]
    )
    payments_total = _money(payments.aggregate(total=Sum("amount"))["total"])

    status_rows = list(orders.values("status").annotate(total=Count("id")).order_by("-total"))
    enquiry_rows = list(enquiries.values("status").annotate(total=Count("id")).order_by("-total"))

    stock_in = _money(stock.filter(
        transaction_type=StockTransaction.TransactionType.IN
    ).aggregate(total=Sum("quantity"))["total"])
    stock_out = _money(stock.filter(
        transaction_type=StockTransaction.TransactionType.OUT
    ).aggregate(total=Sum("quantity"))["total"])

    active_staff = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).count()
    present = StaffAttendance.objects.filter(
        date__range=(start, end), status=StaffAttendance.Status.PRESENT
    ).count()
    absent = StaffAttendance.objects.filter(
        date__range=(start, end), status=StaffAttendance.Status.ABSENT
    ).count()
    leave = StaffAttendance.objects.filter(
        date__range=(start, end), status=StaffAttendance.Status.LEAVE
    ).count()

    overdue = StaffTask.objects.filter(
        due_date__lt=end
    ).exclude(
        status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
    ).count()

    low_stock = Product.objects.filter(
        status=Product.Status.ACTIVE,
        stock_quantity__lte=F("low_stock_threshold"),
    ).count()

    # Cross-module management KPIs.
    purchase_open = PurchaseOrder.objects.filter(
        status__in=[PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIAL]
    ).count()
    purchase_value = _money(
        PurchaseOrder.objects.exclude(status=PurchaseOrder.Status.CANCELLED)
        .aggregate(total=Sum("total"))["total"]
    )
    paid_expenses = _money(
        Expense.objects.filter(
            status=Expense.Status.PAID,
            expense_date__range=(start, end),
        ).aggregate(total=Sum("amount"))["total"]
    )
    delivery_pending = DeliveryRecord.objects.filter(
        status__in=[
            DeliveryRecord.Status.PENDING,
            DeliveryRecord.Status.SCHEDULED,
            DeliveryRecord.Status.READY,
            DeliveryRecord.Status.OUT,
        ]
    ).count()
    active_campaigns = Campaign.objects.filter(status=Campaign.Status.ACTIVE).count()
    open_leads = MarketingLead.objects.filter(
        status__in=[MarketingLead.Status.NEW, MarketingLead.Status.CONTACTED]
    ).count()

    top_products = list(
        Product.objects.filter(status=Product.Status.ACTIVE)
        .order_by("-stock_quantity")[:5]
        .values("name", "sku", "stock_quantity", "selling_price")
    )

    return render(request, "reports/dashboard.html", {
        "title": "Reports & Analytics",
        "start": start,
        "end": end,
        "stats": {
            "orders": orders.exclude(status=SalesOrder.Status.CANCELLED).count(),
            "order_revenue": order_revenue,
            "payments": payments_total,
            "enquiries": enquiries.count(),
            "quotations": quotations.count(),
            "customers": Customer.objects.filter(created_at__date__range=(start, end)).count(),
            "stock_in": stock_in,
            "stock_out": stock_out,
            "active_staff": active_staff,
            "present": present,
            "absent": absent,
            "leave": leave,
            "overdue": overdue,
            "low_stock": low_stock,
            "purchase_open": purchase_open,
            "purchase_value": purchase_value,
            "paid_expenses": paid_expenses,
            "delivery_pending": delivery_pending,
            "active_campaigns": active_campaigns,
            "open_leads": open_leads,
        },
        "order_status": status_rows,
        "enquiry_status": enquiry_rows,
        "top_products": top_products,
    })


def models_F(field):
    from django.db.models import F
    return F(field)


@login_required
@role_required("super_admin", "institution_admin", "manager")
def export_csv(request):
    start, end = _date_range(request)
    orders = SalesOrder.objects.filter(
        created_at__date__range=(start, end)
    ).exclude(status=SalesOrder.Status.CANCELLED).select_related("customer")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="sadaco-sales-report-{start}-{end}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Order No", "Customer", "Item", "Quantity", "Confirmed Price", "Status", "Created"])
    for order in orders:
        writer.writerow([
            order.order_no, order.customer.name, order.item_description,
            order.quantity, order.confirmed_price,
            order.get_status_display(), timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M"),
        ])
    return response


@login_required
@role_required("super_admin", "institution_admin", "manager")
def export_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    )

    start, end = _date_range(request)
    orders = SalesOrder.objects.filter(created_at__date__range=(start, end)).exclude(
        status=SalesOrder.Status.CANCELLED
    ).select_related("customer")
    enquiries = Enquiry.objects.filter(created_at__date__range=(start, end))
    payments = PaymentRecord.objects.filter(
        created_at__date__range=(start, end),
        status__in=[PaymentRecord.Status.RECEIVED, PaymentRecord.Status.VERIFIED],
    )
    stock = StockTransaction.objects.filter(created_at__date__range=(start, end))

    order_value = _money(orders.aggregate(total=Sum("confirmed_price"))["total"])
    payments_total = _money(payments.aggregate(total=Sum("amount"))["total"])
    stock_in = _money(stock.filter(
        transaction_type=StockTransaction.TransactionType.IN
    ).aggregate(total=Sum("quantity"))["total"])
    stock_out = _money(stock.filter(
        transaction_type=StockTransaction.TransactionType.OUT
    ).aggregate(total=Sum("quantity"))["total"])

    active_staff = StaffProfile.objects.filter(status=StaffProfile.Status.ACTIVE).count()
    present = StaffAttendance.objects.filter(
        date__range=(start, end), status=StaffAttendance.Status.PRESENT
    ).count()
    absent = StaffAttendance.objects.filter(
        date__range=(start, end), status=StaffAttendance.Status.ABSENT
    ).count()
    leave = StaffAttendance.objects.filter(
        date__range=(start, end), status=StaffAttendance.Status.LEAVE
    ).count()
    overdue = StaffTask.objects.filter(due_date__lt=end).exclude(
        status__in=[StaffTask.Status.COMPLETED, StaffTask.Status.CANCELLED]
    ).count()
    low_stock = Product.objects.filter(
        status=Product.Status.ACTIVE,
        stock_quantity__lte=F("low_stock_threshold"),
    ).count()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title="SADACO Business Report",
        author="SADACO Management System",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontSize=22, leading=26,
        textColor=colors.HexColor("#0f172a"), spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="ReportSub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="Section", parent=styles["Heading2"], fontSize=13, leading=16,
        textColor=colors.HexColor("#172554"), spaceBefore=12, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="Small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#475569"),
    ))

    story = [
        Paragraph("SADACO Management System", styles["ReportTitle"]),
        Paragraph(
            f"Business Report & Analytics · {start.strftime('%d %b %Y')} — {end.strftime('%d %b %Y')}",
            styles["ReportSub"],
        ),
    ]

    summary = [
        ["Metric", "Value", "Metric", "Value"],
        ["Sales Orders", str(orders.count()), "Order Value", f"Rs. {order_value:,.2f}"],
        ["Payments Received", f"Rs. {payments_total:,.2f}", "Enquiries", str(enquiries.count())],
        ["Stock In", str(stock_in), "Stock Out", str(stock_out)],
        ["Active Staff", str(active_staff), "Present Records", str(present)],
        ["Absent Records", str(absent), "Leave Records", str(leave)],
        ["Low Stock Alerts", str(low_stock), "Overdue Tasks", str(overdue)],
    ]
    t=Table(summary, colWidths=[42*mm, 42*mm, 42*mm, 42*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#172554")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),8),
        ("BACKGROUND",(0,1),(-1,-1),colors.HexColor("#f8fafc")),
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#dbe3ed")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),7),
        ("BOTTOMPADDING",(0,0),(-1,-1),7),
    ]))
    story += [t, Spacer(1, 5)]

    story.append(Paragraph("Sales Orders", styles["Section"]))
    order_data=[["Order No","Customer","Item","Qty","Value","Status"]]
    for o in orders[:35]:
        order_data.append([
            o.order_no, o.customer.name[:24], o.item_description[:28],
            str(o.quantity), f"Rs. {o.confirmed_price:,.2f}", o.get_status_display()
        ])
    if len(order_data)==1:
        order_data.append(["—","No orders in selected period.","","","",""])
    ot=Table(order_data, colWidths=[27*mm,34*mm,43*mm,15*mm,28*mm,32*mm], repeatRows=1)
    ot.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#eff6ff")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#1e3a8a")),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),7),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#dbe3ed")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story += [ot]

    story.append(Paragraph("Report Notes", styles["Section"]))
    story.append(Paragraph(
        "This report is generated from the SADACO PostgreSQL database using the selected date range. "
        "Cancelled sales orders are excluded from sales-value totals. Payment totals include received and verified payments.",
        styles["Small"],
    ))

    doc.build(story)
    buffer.seek(0)
    filename=f"sadaco-business-report-{start}-{end}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename, content_type="application/pdf")
