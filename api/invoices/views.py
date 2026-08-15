from datetime import timedelta
from decimal import Decimal

from django.http import FileResponse
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from api.models import (
    BusinessProfile,
    Invoice,
    InvoiceItem,
    Quote,
    AppSettings,
)

from .pdf import generate_invoice_pdf
from .serializers import InvoiceSerializer


def is_admin_user(user):
    return bool(user.is_staff or user.is_superuser)


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


# ============================================================
# INVOICE LIST / CREATE
# ============================================================

@extend_schema(tags=["Invoices"], request=InvoiceSerializer)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def invoice_list_create(request):

    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    # ========================================================
    # GET ALL INVOICES
    # ========================================================

    if request.method == "GET":

        if is_admin:
            invoices = (
                Invoice.objects
                .filter(business=business)
                .select_related("client", "quote")
                .prefetch_related("items")
                .order_by("-created_at")
            )
        else:
            # Client portal user: strictly client's own invoices
            invoices = (
                Invoice.objects
                .filter(client__email__iexact=request.user.email)
                .select_related("client", "quote", "business")
                .prefetch_related("items")
                .order_by("-created_at")
            )

        serializer = InvoiceSerializer(
            invoices,
            many=True,
        )

        return Response({
            "success": True,
            "message": "Invoices retrieved successfully",
            "data": serializer.data,
        })

    # ========================================================
    # CREATE INVOICE
    # ========================================================

    serializer = InvoiceSerializer(data=request.data)

    if serializer.is_valid():
        if serializer.validated_data["client"].business_id != business.id:
            return Response({"success": False, "message": "Client does not belong to your business."}, status=status.HTTP_400_BAD_REQUEST)

        quote = serializer.validated_data.get("quote")
        if quote and quote.business_id != business.id:
            return Response({"success": False, "message": "Quote does not belong to your business."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            settings_obj, _ = AppSettings.objects.select_for_update().get_or_create(business=business)
            provided_invoice_number = request.data.get("invoice_number")
            if provided_invoice_number:
                invoice_number = str(provided_invoice_number).strip()
            else:
                invoice_number = f"{settings_obj.invoice_prefix}-{settings_obj.next_invoice_number:04d}"
                settings_obj.next_invoice_number += 1
                settings_obj.save(update_fields=["next_invoice_number", "updated_at"])

            provided_issue_date = serializer.validated_data.get("issue_date")
            issue_date = provided_issue_date if provided_issue_date else timezone.now().date()

            provided_due_date = serializer.validated_data.get("due_date")
            due_date = provided_due_date if provided_due_date else (issue_date + timedelta(days=settings_obj.invoice_due_days))

            invoice = serializer.save(
                business=business,
                invoice_number=invoice_number,
                issue_date=issue_date,
                due_date=due_date,
                notes=serializer.validated_data.get("notes") or settings_obj.invoice_notes,
                terms=serializer.validated_data.get("terms") or settings_obj.invoice_terms,
            )

        return Response(
            {
                "success": True,
                "message": "Invoice created successfully",
                "data": InvoiceSerializer(
                    invoice
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "success": False,
            "message": "Invoice creation failed",
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


# ============================================================
# INVOICE DETAIL
# ============================================================

@extend_schema(tags=["Invoices"], request=InvoiceSerializer)
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def invoice_detail(request, pk):

    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        invoice = get_object_or_404(
            Invoice.objects
            .select_related(
                "client",
                "quote",
            )
            .prefetch_related(
                "items",
            ),
            pk=pk,
            business=business,
        )
    else:
        # Client user - strictly client's own invoice
        invoice = get_object_or_404(
            Invoice.objects
            .select_related(
                "client",
                "quote",
                "business",
            )
            .prefetch_related(
                "items",
            ),
            pk=pk,
            client__email__iexact=request.user.email,
        )

    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        serializer = InvoiceSerializer(
            invoice
        )

        return Response({
            "success": True,
            "message": "Invoice retrieved successfully",
            "data": serializer.data,
        })

    # ========================================================
    # UPDATE
    # ========================================================

    if request.method in [
        "PUT",
        "PATCH",
    ]:

        serializer = InvoiceSerializer(
            invoice,
            data=request.data,
            partial=(
                request.method == "PATCH"
            ),
        )

        if serializer.is_valid():

            client = serializer.validated_data.get("client")
            quote = serializer.validated_data.get("quote")
            if client and client.business_id != business.id:
                return Response({"success": False, "message": "Client does not belong to your business."}, status=status.HTTP_400_BAD_REQUEST)
            if quote and quote.business_id != business.id:
                return Response({"success": False, "message": "Quote does not belong to your business."}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()

            return Response({
                "success": True,
                "message": "Invoice updated successfully",
                "data": serializer.data,
            })

        return Response(
            {
                "success": False,
                "message": "Invoice update failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ========================================================
    # DELETE
    # ========================================================

    try:
        invoice.delete()
    except ProtectedError:
        return Response(
            {"success": False, "message": "This invoice has payments or receipts and cannot be deleted."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "success": True,
            "message": "Invoice deleted successfully",
        },
        status=status.HTTP_204_NO_CONTENT,
    )


# ============================================================
# INVOICE PDF
# ============================================================

@extend_schema(
    tags=["Invoices"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_pdf(request, pk):
    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        invoice = get_object_or_404(
            Invoice.objects
            .select_related(
                "business",
                "client",
                "quote",
            )
            .prefetch_related(
                "items",
            ),
            pk=pk,
            business=business,
        )
    else:
        invoice = get_object_or_404(
            Invoice.objects
            .select_related(
                "business",
                "client",
                "quote",
            )
            .prefetch_related(
                "items",
            ),
            pk=pk,
            client__email__iexact=request.user.email,
        )

    template_name = request.GET.get("template")
    buffer = generate_invoice_pdf(invoice, template=template_name)

    buffer.seek(0)

    filename = (
        f"{invoice.invoice_number or 'invoice'}.pdf"
    )

    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


# ============================================================
# SEND INVOICE
# ============================================================

@extend_schema(tags=["Invoices"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_invoice(request, pk):

    business = get_user_business(
        request.user
    )

    invoice = get_object_or_404(
        Invoice,
        pk=pk,
        business=business,
    )

    if not invoice.client.email:
        return Response(
            {"success": False, "message": "The invoice client does not have an email address."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pdf_buffer = generate_invoice_pdf(invoice)

        email_message = EmailMessage(
            subject=f"Invoice {invoice.invoice_number}",
            body=(
                f"Hello {invoice.client.name},\n\n"
                f"Your invoice {invoice.invoice_number} for {invoice.total:.2f} is ready.\n\n"
                f"Issue Date: {invoice.issue_date}\n"
                f"Due Date: {invoice.due_date}\n"
                f"Total: {invoice.total:.2f}\n\n"
                "Please find the invoice attached as a PDF.\n\n"
                "Thank you for your business."
            ),
            from_email=business.email or None,
            to=[invoice.client.email],
        )

        email_message.attach(
            f"{invoice.invoice_number or 'invoice'}.pdf",
            pdf_buffer.read(),
            "application/pdf",
        )

        email_message.send(fail_silently=False)

    except Exception:
        return Response(
            {"success": False, "message": "Unable to send the invoice email. Check the email settings."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if invoice.status == Invoice.Status.DRAFT:
        invoice.status = Invoice.Status.SENT
        invoice.save(update_fields=["status", "updated_at"])

    return Response({
        "success": True,
        "message": "Invoice email sent successfully.",
        "data": InvoiceSerializer(invoice).data,
    })


# ============================================================
# CREATE INVOICE FROM QUOTE
# ============================================================

@extend_schema(tags=["Invoices"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invoice_from_quote(request):

    """
    POST /api/invoices/from-quote/

    Body:

    {
        "quote_id": 1
    }

    Creates a new Invoice and InvoiceItems
    from an existing Quote.
    """

    business = get_user_business(
        request.user
    )

    quote_id = request.data.get(
        "quote_id"
    )

    if not quote_id:

        return Response(
            {
                "success": False,
                "message": (
                    "quote_id is required."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ========================================================
    # GET QUOTE
    # ========================================================

    quote = get_object_or_404(
        Quote.objects
        .select_related(
            "client",
        )
        .prefetch_related(
            "items",
        ),
        pk=quote_id,
        business=business,
    )

    # ========================================================
    # CHECK CONVERSION
    # ========================================================

    if (
        quote.status
        == Quote.Status.CONVERTED
    ):

        return Response(
            {
                "success": False,
                "message": (
                    "Quote is already "
                    "converted to an invoice."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        # ========================================================
        # APP SETTINGS
        # ========================================================

        settings_obj = AppSettings.objects.select_for_update().get_or_create(
            business=business
        )[0]

        invoice_number = (
            f"{settings_obj.invoice_prefix}"
            f"-"
            f"{settings_obj.next_invoice_number:04d}"
        )

        settings_obj.next_invoice_number += 1

        settings_obj.save(
            update_fields=[
                "next_invoice_number",
            ]
        )

        # ========================================================
        # DATES
        # ========================================================

        issue_date = timezone.now().date()

        due_date = (
            issue_date
            + timedelta(
                days=7
            )
        )

        # ========================================================
        # CREATE INVOICE
        # ========================================================

        invoice = Invoice.objects.create(
            business=business,
            client=quote.client,
            quote=quote,
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=due_date,
            status=Invoice.Status.DRAFT,
            subtotal=quote.subtotal,
            discount=quote.discount,
            tax=quote.tax,
            total=quote.total,
            paid_amount=Decimal("0.00"),
            balance_due=quote.total,
            notes=quote.notes,
            terms=quote.terms,
        )

        # ========================================================
        # COPY ITEMS
        # ========================================================

        invoice_items = []

        for item in quote.items.all():

            invoice_items.append(
                InvoiceItem(
                    invoice=invoice,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    tax_rate=item.tax_rate,
                    discount=item.discount,
                    amount=item.amount,
                )
            )

        if invoice_items:

            InvoiceItem.objects.bulk_create(
                invoice_items
            )

        # ========================================================
        # MARK QUOTE CONVERTED
        # ========================================================

        quote.status = (
            Quote.Status.CONVERTED
        )

        quote.save(
            update_fields=[
                "status",
            ]
        )

        # ========================================================
        # RESPONSE
        # ========================================================

        return Response(
            {
                "success": True,
                "message": (
                    "Invoice created "
                    "from quote successfully"
                ),
                "data": InvoiceSerializer(
                    invoice
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
