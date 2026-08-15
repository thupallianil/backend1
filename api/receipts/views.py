from io import BytesIO
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.http import FileResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import AppSettings, BusinessProfile, Receipt
from .serializers import ReceiptSerializer


def is_admin_user(user):
    return bool(user.is_staff or user.is_superuser)


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def receipt_list(request):
    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        receipts = Receipt.objects.filter(
            business=business
        ).order_by("-created_at")
    else:
        # Client portal user: strictly client's own receipts
        receipts = Receipt.objects.filter(
            invoice__client__email__iexact=request.user.email
        ).order_by("-created_at")

    serializer = ReceiptSerializer(
        receipts,
        many=True,
    )

    return Response({
        "success": True,
        "message": "Receipts retrieved successfully",
        "data": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def receipt_detail(request, pk):
    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        receipt = get_object_or_404(
            Receipt,
            pk=pk,
            business=business,
        )
    else:
        # Client user: strictly client's own receipt
        receipt = get_object_or_404(
            Receipt,
            pk=pk,
            invoice__client__email__iexact=request.user.email,
        )

    return Response({
        "success": True,
        "message": "Receipt retrieved successfully",
        "data": ReceiptSerializer(receipt).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def receipt_pdf(request, pk):
    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        receipt = get_object_or_404(
            Receipt.objects.select_related("business", "invoice", "payment", "invoice__client"),
            pk=pk,
            business=business,
        )
    else:
        # Client user: strictly client's own receipt PDF
        receipt = get_object_or_404(
            Receipt.objects.select_related("business", "invoice", "payment", "invoice__client"),
            pk=pk,
            invoice__client__email__iexact=request.user.email,
        )

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Receipt {receipt.receipt_number}",
        author="Payment Settlement System",
    )

    # Fetch dynamic settings
    app_settings = AppSettings.objects.filter(business=receipt.business).first() or AppSettings.objects.first()
    translations = dict(getattr(app_settings, "translations", {}) or {})
    pdf_settings = dict(getattr(app_settings, "pdf_settings", {}) or {})

    # Brand color
    accent_hex = pdf_settings.get("accentColor") or "#0f766e"  # Teal / Emerald
    try:
        accent_color = colors.HexColor(accent_hex)
    except Exception:
        accent_color = colors.HexColor("#0f766e")

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RecTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
    )

    doc_type_style = ParagraphStyle(
        "RecType",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        textColor=accent_color,
        alignment=2,
    )

    heading_style = ParagraphStyle(
        "RecHeading",
        parent=styles["Heading2"],
        fontSize=10,
        leading=13,
        textColor=accent_color,
        fontName="Helvetica-Bold",
    )

    normal_style = ParagraphStyle(
        "RecNormal",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    elements = []

    # Business data
    biz = receipt.business
    biz_name = getattr(biz, "business_name", None) or "Business Profile"
    address_parts = [
        getattr(biz, "address", None),
        getattr(biz, "city", None),
        getattr(biz, "state", None),
        getattr(biz, "country", None),
        getattr(biz, "postal_code", None),
    ]
    address = ", ".join(str(v) for v in address_parts if v)
    biz_lines = []
    if address:
        biz_lines.append(address)
    if getattr(biz, "email", None):
        biz_lines.append(f"Email: {biz.email}")
    if getattr(biz, "phone", None):
        biz_lines.append(f"Phone: {biz.phone}")
    if getattr(biz, "tax_number", None):
        biz_lines.append(f"GSTIN / Tax ID: {biz.tax_number}")
    biz_text = "<br/>".join(biz_lines) or "—"

    # Payment details
    payment = receipt.payment
    method_raw = getattr(payment, "method", "cash")
    method_display = payment.get_method_display() if payment else "Cash"
    if method_raw == "cash":
        voucher_title = "OFFICIAL CASH RECEIPT VOUCHER"
    elif method_raw == "card":
        voucher_title = "CREDIT / DEBIT CARD TRANSACTION RECEIPT"
    elif method_raw == "bank":
        voucher_title = "BANK WIRE SETTLEMENT RECEIPT"
    elif method_raw == "upi":
        voucher_title = "DIGITAL UPI PAYMENT RECEIPT"
    else:
        voucher_title = "OFFICIAL PAYMENT RECEIPT"

    txn_ref = getattr(payment, "transaction_id", None) or getattr(payment, "gateway_payment_id", None) or "—"

    # ========================================================
    # TOP HEADER
    # ========================================================
    top_header_data = [
        [
            Paragraph(f"<b>{biz_name}</b><br/><font size=8 color='#64748b'>{biz_text}</font>", normal_style),
            Paragraph(f"<b>{voucher_title}</b><br/><font size=9 color='#047857'><b>Receipt #:</b> {receipt.receipt_number}<br/><b>Date:</b> {receipt.issued_date}<br/><b>Status:</b> CLEARED & SETTLED</font>", ParagraphStyle("RecTopR", parent=normal_style, alignment=2)),
        ]
    ]
    top_header_table = Table(top_header_data, colWidths=[105 * mm, 77 * mm])
    top_header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(top_header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=2, spaceAfter=8))

    # ========================================================
    # CLIENT / RECEIVED FROM BOX
    # ========================================================
    invoice = receipt.invoice
    client = getattr(invoice, "client", None)
    client_name = getattr(client, "name", None) or getattr(client, "client_name", None) or "Valued Client"
    client_company = getattr(client, "company_name", None) or ""
    client_email = getattr(client, "email", None) or "—"
    client_phone = getattr(client, "phone", None) or "—"

    client_box_text = f"<b>{client_name}</b>"
    if client_company:
        client_box_text += f"<br/>{client_company}"
    client_box_text += f"<br/>Email: {client_email} • Phone: {client_phone}"

    recv_data = [
        [
            Paragraph("<b>RECEIVED FROM:</b>", heading_style),
            Paragraph("<b>SETTLEMENT METHOD:</b>", heading_style),
        ],
        [
            Paragraph(client_box_text, normal_style),
            Paragraph(f"<b>Mode:</b> {method_display}<br/><b>Reference / UTR:</b> {txn_ref}<br/><b>Invoice Ref:</b> {invoice.invoice_number if invoice else '—'}", normal_style),
        ]
    ]
    recv_table = Table(recv_data, colWidths=[91 * mm, 91 * mm])
    recv_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(recv_table)
    elements.append(Spacer(1, 10))

    # ========================================================
    # SETTLEMENT SUMMARY TABLE
    # ========================================================
    inv_total = invoice.total if invoice and invoice.total is not None else Decimal("0.00")
    inv_paid = invoice.paid_amount if invoice and invoice.paid_amount is not None else Decimal("0.00")
    inv_bal = invoice.balance_due if invoice and invoice.balance_due is not None else Decimal("0.00")

    summary_rows = [
        [
            "Invoice Number",
            "Total Invoiced",
            "Amount Received in this Receipt",
            "Total Paid to Date",
            "Remaining Balance",
        ],
        [
            str(invoice.invoice_number if invoice else "—"),
            f"{inv_total:.2f}",
            f"{receipt.amount:.2f}",
            f"{inv_paid:.2f}",
            f"{inv_bal:.2f}",
        ]
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[38 * mm, 34 * mm, 44 * mm, 33 * mm, 33 * mm],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#ecfdf5")),
        ("FONTNAME", (2, 1), (2, 1), "Helvetica-Bold"),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # ========================================================
    # HIGHLIGHT AMOUNT BOX
    # ========================================================
    amt_box = [
        [
            Paragraph(f"<font size=11 color='#065f46'><b>NET AMOUNT RECEIVED:</b></font>", normal_style),
            Paragraph(f"<font size=14 color='#065f46'><b>₹ {receipt.amount:.2f}</b></font>", ParagraphStyle("AmtR", parent=normal_style, alignment=2)),
        ]
    ]
    amt_table = Table(amt_box, colWidths=[100 * mm, 82 * mm])
    amt_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d1fae5")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#059669")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(amt_table)
    elements.append(Spacer(1, 8))

    # Notes
    notes_text = receipt.notes or getattr(payment, "notes", None) or "Payment settled and reconciled with digital audit logs."
    elements.append(Paragraph(f"<b>Settlement Notes:</b> {notes_text}", normal_style))
    elements.append(Spacer(1, 12))

    # ========================================================
    # OFFICIAL STAMP & AUTHORIZED SIGNATURE
    # ========================================================
    sig_data = [
        [
            Paragraph(
                "<font size=8 color='#059669'><b>DIGITALLY VERIFIED VOUCHER</b><br/>This document acknowledges receipt of funds.<br/>Transaction verified via system banking reconciliation.</font>",
                normal_style,
            ),
            Paragraph(
                f"<b>For {biz_name}</b><br/><br/><br/>________________________________<br/><b>Authorized Cashier / Accounts Signatory</b>",
                ParagraphStyle("RecSigR", parent=normal_style, alignment=2),
            ),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[95 * mm, 87 * mm])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    elements.append(sig_table)

    document.build(elements)
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"Receipt_{receipt.receipt_number}.pdf",
        content_type="application/pdf",
    )
