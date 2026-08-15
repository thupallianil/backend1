from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from api.models import AppSettings


def generate_invoice_pdf(invoice, template=None):
    """
    Generate a dynamic, high-precision PDF for an Invoice model instance.
    Supports 4 Distinct Template Themes:
    - template1: Modern Corporate (Dark banner, sleek navy grid, high contrast)
    - template2: Clean Minimal (Airy whitespace, thin rules, minimal slate)
    - template3: Tech Indigo / Vibrant (Rich indigo header, pill styling, modern highlights)
    - template4: Formal Executive (Boxed layout, double border, authorized signature block)
    """
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Invoice {invoice.invoice_number}",
        author="Invoicing System",
    )

    # 1. Fetch Dynamic Settings
    business = invoice.business
    app_settings = None
    if business:
        app_settings = AppSettings.objects.filter(business=business).first()
    if not app_settings:
        app_settings = AppSettings.objects.first()

    # Determine Active Template
    if not template:
        template = getattr(app_settings, "invoice_template", None) or "template1"
    template = str(template).lower().strip()

    translations = dict(getattr(app_settings, "translations", {}) or {})
    pdf_settings = dict(getattr(app_settings, "pdf_settings", {}) or {})
    payment_settings = dict(getattr(app_settings, "payment_settings", {}) or {})

    # Palette setup by template
    if template == "template3":
        primary_color = colors.HexColor("#4f46e5")  # Indigo
        accent_color = colors.HexColor("#6366f1")
        header_bg = colors.HexColor("#312e81")       # Deep indigo
        header_text = colors.white
        table_header_bg = colors.HexColor("#4f46e5")
        totals_bg = colors.HexColor("#e0e7ff")
    elif template == "template2":
        primary_color = colors.HexColor("#0f172a")  # Minimal slate
        accent_color = colors.HexColor("#64748b")
        header_bg = colors.white
        header_text = colors.HexColor("#0f172a")
        table_header_bg = colors.HexColor("#f8fafc")
        totals_bg = colors.HexColor("#f8fafc")
    elif template == "template4":
        primary_color = colors.HexColor("#1e293b")  # Executive Dark Slate
        accent_color = colors.HexColor("#334155")
        header_bg = colors.HexColor("#f1f5f9")
        header_text = colors.HexColor("#0f172a")
        table_header_bg = colors.HexColor("#1e293b")
        totals_bg = colors.HexColor("#e2e8f0")
    else:  # template1: Modern Corporate
        primary_color = colors.HexColor("#0f172a")
        accent_color = colors.HexColor("#0d9488")   # Teal
        header_bg = colors.HexColor("#020617")       # Obsidian
        header_text = colors.white
        table_header_bg = colors.HexColor("#0f172a")
        totals_bg = colors.HexColor("#f1f5f9")

    # Document Labels
    invoice_title = translations.get("invoiceLabel") or "TAX INVOICE"
    label_service = translations.get("labelService") or "Description"
    label_qty = translations.get("labelHrsQty") or "Qty"
    label_rate = translations.get("labelRatePrice") or "Unit Price"
    label_total = translations.get("labelTotal") or "Amount"
    label_subtotal = translations.get("labelSubTotal") or "Subtotal"
    label_discount = translations.get("labelDiscount") or "Discount"
    label_due = translations.get("labelTotalDue") or "Total Due"

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=header_text if header_bg != colors.white else primary_color,
        alignment=0,
    )

    doc_type_style = ParagraphStyle(
        "DocTypeTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        textColor=colors.white if header_bg != colors.white else primary_color,
        alignment=2,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=10,
        leading=13,
        textColor=primary_color,
        fontName="Helvetica-Bold",
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
    )

    bold_style = ParagraphStyle(
        "CustomBold",
        parent=normal_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"),
    )

    elements = []

    # Business data
    business_name = getattr(business, "business_name", None) or "Business"
    address_parts = [
        getattr(business, "address", None),
        getattr(business, "city", None),
        getattr(business, "state", None),
        getattr(business, "country", None),
        getattr(business, "postal_code", None),
    ]
    address = ", ".join(str(v) for v in address_parts if v)
    biz_lines = []
    if address:
        biz_lines.append(address)
    if getattr(business, "email", None):
        biz_lines.append(f"Email: {business.email}")
    if getattr(business, "phone", None):
        biz_lines.append(f"Phone: {business.phone}")
    if getattr(business, "tax_number", None):
        biz_lines.append(f"GSTIN / Tax ID: {business.tax_number}")
    biz_text = "<br/>".join(biz_lines) or "—"

    try:
        status_display = invoice.get_status_display().upper()
    except Exception:
        status_display = str(getattr(invoice, "status", "DRAFT")).upper()

    # ========================================================
    # 1. HEADER SECTION (Styled per Template)
    # ========================================================
    if template in ["template1", "template3"]:
        # Dark Banner Header
        header_table_data = [
            [
                Paragraph(f"<b>{business_name}</b><br/><font size=8 color='#94a3b8'>{biz_text}</font>", ParagraphStyle("H1", parent=normal_style, textColor=colors.white)),
                Paragraph(f"<b>{invoice_title.upper()}</b><br/><font size=9 color='#cbd5e1'><b>Invoice #:</b> {invoice.invoice_number or '—'}<br/><b>Date:</b> {invoice.issue_date or '—'}<br/><b>Due:</b> {invoice.due_date or '—'}<br/><b>Status:</b> {status_display}</font>", ParagraphStyle("H2", parent=normal_style, textColor=colors.white, alignment=2)),
            ]
        ]
        hdr_table = Table(header_table_data, colWidths=[110 * mm, 72 * mm])
        hdr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), header_bg),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(hdr_table)
        elements.append(Spacer(1, 10))

    elif template == "template2":
        # Minimalist Clean Header
        header_table_data = [
            [
                Paragraph(f"<font size=16><b>{business_name.upper()}</b></font><br/><font size=8 color='#64748b'>{biz_text}</font>", normal_style),
                Paragraph(f"<font size=14 color='#0f172a'><b>{invoice_title.upper()}</b></font><br/><font size=8.5 color='#475569'><b>Invoice #:</b> {invoice.invoice_number or '—'}<br/><b>Issue Date:</b> {invoice.issue_date or '—'}<br/><b>Due Date:</b> {invoice.due_date or '—'}<br/><b>Status:</b> {status_display}</font>", ParagraphStyle("MinR", parent=normal_style, alignment=2)),
            ]
        ]
        hdr_table = Table(header_table_data, colWidths=[110 * mm, 72 * mm])
        hdr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(hdr_table)
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=8))

    else:
        # Template 4: Formal Executive Boxed Header
        header_table_data = [
            [
                Paragraph(f"<b>{business_name}</b><br/><font size=8 color='#334155'>{biz_text}</font>", normal_style),
                Paragraph(f"<b>{invoice_title.upper()}</b><br/><font size=8.5><b>Invoice No:</b> {invoice.invoice_number or '—'}<br/><b>Date:</b> {invoice.issue_date or '—'}<br/><b>Due:</b> {invoice.due_date or '—'}<br/><b>Status:</b> {status_display}</font>", ParagraphStyle("ExecR", parent=normal_style, alignment=2)),
            ]
        ]
        hdr_table = Table(header_table_data, colWidths=[110 * mm, 72 * mm])
        hdr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0f172a")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(hdr_table)
        elements.append(Spacer(1, 10))

    # ========================================================
    # 2. CLIENT / BILL TO SECTION
    # ========================================================
    client = invoice.client
    client_lines = []
    if client:
        if getattr(client, "name", None):
            client_lines.append(f"<b>{client.name}</b>")
        if getattr(client, "company_name", None):
            client_lines.append(str(client.company_name))
        if getattr(client, "email", None):
            client_lines.append(f"Email: {client.email}")
        if getattr(client, "phone", None):
            client_lines.append(f"Phone: {client.phone}")
        if getattr(client, "address", None):
            client_lines.append(str(client.address))
        if getattr(client, "tax_number", None):
            client_lines.append(f"GSTIN: {client.tax_number}")

    client_text = "<br/>".join(client_lines) or "Client details unavailable"

    bill_to_box = [
        [Paragraph("<b>BILL TO:</b>", heading_style)],
        [Paragraph(client_text, normal_style)],
    ]
    bill_to_table = Table(bill_to_box, colWidths=[182 * mm])
    bill_to_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc") if template != "template2" else colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0") if template != "template4" else colors.HexColor("#0f172a")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(bill_to_table)
    elements.append(Spacer(1, 10))

    # ========================================================
    # 3. LINE ITEMS TABLE
    # ========================================================
    item_rows = [
        [
            "#",
            label_service,
            label_qty,
            label_rate,
            "Tax %",
            "Discount",
            label_total,
        ]
    ]

    items = invoice.items.all()
    for index, item in enumerate(items, start=1):
        q = item.quantity if item.quantity is not None else Decimal("0")
        up = item.unit_price if item.unit_price is not None else Decimal("0")
        tr = item.tax_rate if item.tax_rate is not None else Decimal("0")
        dc = item.discount if item.discount is not None else Decimal("0")
        amt = item.amount if item.amount is not None else Decimal("0")

        item_rows.append([
            str(index),
            str(item.description or ""),
            str(q),
            f"{up:.2f}",
            f"{tr:.1f}%",
            f"{dc:.2f}",
            f"{amt:.2f}",
        ])

    if len(item_rows) == 1:
        item_rows.append(["", "No items", "", "", "", "", ""])

    items_table = Table(
        item_rows,
        repeatRows=1,
        colWidths=[8 * mm, 62 * mm, 15 * mm, 25 * mm, 18 * mm, 22 * mm, 32 * mm],
    )

    t_header_text_color = colors.HexColor("#0f172a") if template == "template2" else colors.white
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), table_header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), t_header_text_color),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0") if template != "template4" else colors.HexColor("#0f172a")),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4.5),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 8))

    # ========================================================
    # 4. TOTALS SUMMARY
    # ========================================================
    subtotal = invoice.subtotal or Decimal("0")
    discount = invoice.discount or Decimal("0")
    tax = invoice.tax or Decimal("0")
    total = invoice.total or Decimal("0")
    paid_amount = invoice.paid_amount or Decimal("0")
    balance_due = invoice.balance_due or Decimal("0")

    totals_data = [
        [label_subtotal, f"{subtotal:.2f}"],
        [label_discount, f"-{discount:.2f}"],
        ["Tax / GST", f"{tax:.2f}"],
        ["Grand Total", f"{total:.2f}"],
        ["Paid Amount", f"{paid_amount:.2f}"],
        [f"<b>{label_due}</b>", f"<b>{balance_due:.2f}</b>"],
    ]

    totals_table = Table(totals_data, colWidths=[42 * mm, 35 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0") if template != "template4" else colors.HexColor("#0f172a")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("BACKGROUND", (0, 5), (-1, 5), totals_bg),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 8))

    # ========================================================
    # 5. PAYMENT & SETTLEMENT BOX
    # ========================================================
    upi_id = payment_settings.get("upiId")
    bank_name = payment_settings.get("bankName")
    acc_num = payment_settings.get("accountNumber")
    ifsc = payment_settings.get("ifscCode") or payment_settings.get("ifsc")

    pay_lines = []
    if upi_id:
        pay_lines.append(f"<b>UPI ID:</b> {upi_id}")
    if bank_name:
        pay_lines.append(f"<b>Bank:</b> {bank_name} | <b>A/C:</b> {acc_num or '—'} | <b>IFSC:</b> {ifsc or '—'}")

    if pay_lines:
        pay_text = "<br/>".join(pay_lines)
        pay_box = [
            [Paragraph("<b>PAYMENT SETTLEMENT DETAILS</b>", heading_style)],
            [Paragraph(pay_text, normal_style)],
        ]
        pay_table = Table(pay_box, colWidths=[182 * mm])
        pay_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(pay_table)
        elements.append(Spacer(1, 8))

    # ========================================================
    # 6. NOTES & TERMS
    # ========================================================
    invoice_notes = (invoice.notes.strip() if invoice.notes and str(invoice.notes).strip() else None) or getattr(app_settings, "invoice_notes", "")
    if invoice_notes:
        elements.append(Paragraph("<b>Notes:</b>", heading_style))
        elements.append(Paragraph(str(invoice_notes).replace("\n", "<br/>"), normal_style))
        elements.append(Spacer(1, 4))

    invoice_terms = (invoice.terms.strip() if invoice.terms and str(invoice.terms).strip() else None) or getattr(app_settings, "invoice_terms", "")
    if invoice_terms:
        elements.append(Paragraph("<b>Terms & Conditions:</b>", heading_style))
        elements.append(Paragraph(str(invoice_terms).replace("\n", "<br/>"), normal_style))
        elements.append(Spacer(1, 4))

    # Formal Executive Authorized Signature Box
    if template == "template4":
        elements.append(Spacer(1, 8))
        sig_data = [
            [
                Paragraph("<font size=8 color='#64748b'>Issued By Computer System</font>", normal_style),
                Paragraph(f"<b>For {business_name}</b><br/><br/><br/>________________________<br/><b>Authorized Signatory</b>", ParagraphStyle("SigR", parent=normal_style, alignment=2)),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[100 * mm, 82 * mm])
        sig_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        elements.append(sig_table)
    else:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("<font size=8 color='#94a3b8'>Thank you for your business.</font>", normal_style))

    # Build PDF
    document.build(elements)
    buffer.seek(0)
    return buffer