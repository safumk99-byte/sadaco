from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Quotation


def quotation_pdf_response(quotation):
    """Render a sent quotation from its immutable company/tax snapshots."""
    snapshot = quotation.company_details_snapshot or {}
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"Quotation {quotation.quotation_no}",
        author=snapshot.get("company_name") or "SADACO GROUP OF COMPANIES",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CompanyTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=17, leading=21, textColor=colors.HexColor("#173b70")))
    styles.add(ParagraphStyle(name="SmallRight", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="SmallText", parent=styles["Normal"], fontSize=8, leading=10))
    story = []
    logo = Path(settings.BASE_DIR) / "static" / "images" / "sadaco-logo-blue.png"
    if logo.exists():
        try:
            story.append(Image(str(logo), width=34 * mm, height=17 * mm, kind="proportional"))
        except Exception:
            pass
    story.append(Paragraph(escape(snapshot.get("company_name") or "SADACO GROUP OF COMPANIES"), styles["CompanyTitle"]))
    company_lines = [
        snapshot.get("company_address", ""),
        snapshot.get("company_phone", ""),
        snapshot.get("company_email", ""),
        snapshot.get("company_website", ""),
    ]
    company_lines = [escape(str(x)) for x in company_lines if x]
    if company_lines:
        story.append(Paragraph("<br/>".join(company_lines), styles["SmallText"]))
    story.extend([Spacer(1, 8 * mm), Paragraph("QUOTATION", styles["Heading1"])])
    story.append(Paragraph(
        f"<b>Quotation No:</b> {escape(quotation.quotation_no)}"
        f" &nbsp;&nbsp; <b>Date:</b> {quotation.created_at.strftime('%d-%m-%Y')}"
        f" &nbsp;&nbsp; <b>Valid Until:</b> {quotation.valid_until.strftime('%d-%m-%Y') if quotation.valid_until else '—'}",
        styles["Normal"],
    ))
    customer = quotation.customer
    customer_lines = [customer.name, customer.phone, customer.email, customer.address]
    story.extend([Spacer(1, 4 * mm), Paragraph("<b>Customer Details</b>", styles["Heading2"])])
    story.append(Paragraph("<br/>".join(escape(str(x)) for x in customer_lines if x), styles["Normal"]))
    if quotation.product_id and quotation.product.image:
        try:
            with quotation.product.image.open("rb") as image_file:
                story.append(Image(BytesIO(image_file.read()), width=38 * mm, height=38 * mm, kind="proportional"))
        except Exception:
            pass
    if quotation.item_description:
        story.extend([Spacer(1, 3 * mm), Paragraph(f"<b>Product / Service:</b> {escape(quotation.item_description)}", styles["Normal"])])
    if quotation.dimensions:
        story.append(Paragraph(f"<b>Dimensions:</b> {escape(quotation.dimensions)}", styles["Normal"]))
    data = [["Category", "Description", "Dimensions", "Qty", "Unit", "Unit Price", "Amount"]]
    for item in quotation.line_items.all():
        data.append([
            item.get_category_display(), Paragraph(escape(item.description), styles["SmallText"]),
            item.dimensions or "—", str(item.quantity), item.unit or "—",
            f"₹{item.unit_price:,.2f}", f"₹{item.line_total:,.2f}",
        ])
    table = Table(data, colWidths=[24*mm, 43*mm, 25*mm, 13*mm, 15*mm, 27*mm, 27*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#173b70")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (3,1), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.extend([Spacer(1, 5 * mm), table, Spacer(1, 4 * mm)])
    discount_label = (
        f"Discount (₹{quotation.discount_amount:,.2f} fixed)"
        if quotation.discount_type == "amount"
        else f"Discount ({quotation.discount_percent}%)"
    )
    totals = [
        ["Subtotal", f"₹{quotation.subtotal:,.2f}"],
        [discount_label, f"- ₹{quotation.discount_amount:,.2f}"],
    ]
    if quotation.tax_rate is not None:
        tax_label = snapshot.get("tax_label") or "Tax"
        totals.append([f"{tax_label} ({quotation.tax_rate}%)", f"₹{quotation.tax_amount:,.2f}"])
    totals.extend([["Total", f"₹{quotation.quoted_price:,.2f}"], ["Advance", f"₹{quotation.advance_required:,.2f}"]])
    total_table = Table(totals, colWidths=[125*mm, 49*mm], hAlign="RIGHT")
    total_table.setStyle(TableStyle([
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("FONTNAME", (0,-2), (-1,-2), "Helvetica-Bold"),
        ("LINEABOVE", (0,-2), (-1,-2), 0.8, colors.HexColor("#173b70")),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(total_table)
    if quotation.delivery_timeline:
        story.extend([Spacer(1, 4 * mm), Paragraph(f"<b>Delivery / Installation:</b> {escape(quotation.delivery_timeline)}", styles["Normal"])])
    if quotation.terms:
        story.extend([Spacer(1, 4 * mm), Paragraph("<b>Terms & Conditions</b>", styles["Heading2"]), Paragraph(escape(quotation.terms).replace("\n", "<br/>"), styles["Normal"])])
    story.extend([Spacer(1, 12 * mm), Paragraph("Thank you for your enquiry.", styles["SmallText"])])
    doc.build(story)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{quotation.quotation_no}.pdf"'
    return response
