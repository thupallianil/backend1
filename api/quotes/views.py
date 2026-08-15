from datetime import timedelta

from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.models import (
    AppSettings,
    BusinessProfile,
    Invoice,
    InvoiceItem,
    Quote,
)

from api.invoices.serializers import InvoiceSerializer
from .serializers import QuoteSerializer


def is_admin_user(user):
    return bool(user.is_staff or user.is_superuser)


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


# ============================================================
# LIST / CREATE
# ============================================================

@extend_schema(tags=["Quotes"], request=QuoteSerializer)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quote_list_create(request):

    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if request.method == "GET":

        if is_admin:
            quotes = Quote.objects.filter(
                business=business
            ).select_related(
                "client"
            ).prefetch_related(
                "items"
            ).order_by(
                "-created_at"
            )
        else:
            # Client portal user: strictly client's own quotes
            quotes = Quote.objects.filter(
                client__email__iexact=request.user.email
            ).select_related(
                "client", "business"
            ).prefetch_related(
                "items"
            ).order_by(
                "-created_at"
            )

        serializer = QuoteSerializer(
            quotes,
            many=True,
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    with transaction.atomic():
        app_settings, _ = (
            AppSettings.objects.select_for_update()
            .get_or_create(
                business=business
            )
        )

        data = request.data.copy()
        provided_quote_number = data.pop("quote_number", None)

        if provided_quote_number:
            quote_number = str(provided_quote_number).strip()
        else:
            quote_number = (
                f"{app_settings.quotation_prefix}-"
                f"{app_settings.next_quotation_number:04d}"
            )
            app_settings.next_quotation_number += 1
            app_settings.save(
                update_fields=[
                    "next_quotation_number",
                    "updated_at",
                ]
            )

        provided_issue_date = data.pop("issue_date", None)
        provided_expiry_date = data.pop("expiry_date", None)

        data.setdefault(
            "notes",
            app_settings.quotation_notes,
        )

        data.setdefault(
            "terms",
            app_settings.quotation_terms,
        )

        serializer = QuoteSerializer(
            data=data
        )

        serializer.is_valid(
            raise_exception=True
        )

        if provided_issue_date:
            try:
                from django.utils.dateparse import parse_date
                issue_date = parse_date(str(provided_issue_date)) or timezone.now().date()
            except Exception:
                issue_date = timezone.now().date()
        else:
            issue_date = timezone.now().date()

        if provided_expiry_date:
            try:
                from django.utils.dateparse import parse_date
                expiry_date = parse_date(str(provided_expiry_date)) or (issue_date + timedelta(days=app_settings.quotation_validity_days))
            except Exception:
                expiry_date = issue_date + timedelta(days=app_settings.quotation_validity_days)
        else:
            expiry_date = (
                issue_date
                + timedelta(
                    days=app_settings.quotation_validity_days
                )
            )

        raw_notes = serializer.validated_data.get("notes")
        raw_terms = serializer.validated_data.get("terms")
        final_notes = raw_notes.strip() if raw_notes and str(raw_notes).strip() else app_settings.quotation_notes
        final_terms = raw_terms.strip() if raw_terms and str(raw_terms).strip() else app_settings.quotation_terms

        quote = serializer.save(
            business=business,
            quote_number=quote_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            notes=final_notes,
            terms=final_terms,
        )

    return Response(
        {
            "success": True,
            "message": "Quote created successfully.",
            "data": QuoteSerializer(
                quote
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# DETAIL
# ============================================================

@extend_schema(tags=["Quotes"], request=QuoteSerializer)
@api_view([
    "GET",
    "PUT",
    "PATCH",
    "DELETE",
])
@permission_classes([IsAuthenticated])
def quote_detail(request, pk):

    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        quote = get_object_or_404(
            Quote.objects.select_related(
                "client"
            ).prefetch_related(
                "items"
            ),
            pk=pk,
            business=business,
        )
    else:
        # Client user - strictly client's own quote
        quote = get_object_or_404(
            Quote.objects.select_related(
                "client", "business"
            ).prefetch_related(
                "items"
            ),
            pk=pk,
            client__email__iexact=request.user.email,
        )

    if request.method == "GET":

        return Response({
            "success": True,
            "data": QuoteSerializer(
                quote
            ).data,
        })

    if request.method in [
        "PUT",
        "PATCH",
    ]:

        data = request.data.copy()

        data.pop(
            "quote_number",
            None,
        )

        data.pop(
            "issue_date",
            None,
        )

        serializer = QuoteSerializer(
            quote,
            data=data,
            partial=request.method == "PATCH",
        )

        serializer.is_valid(
            raise_exception=True
        )

        quote = serializer.save()

        # ── Auto-sync linked invoice ──────────────────────────────────────
        # If this quote has a linked invoice that has NOT received any payment
        # yet, automatically push the updated amounts + items to the invoice.
        try:
            linked_invoice = Invoice.objects.filter(
                quote=quote, business=business
            ).first()

            if linked_invoice and linked_invoice.paid_amount == 0:
                linked_invoice.subtotal = quote.subtotal
                linked_invoice.discount = quote.discount
                linked_invoice.tax = quote.tax
                linked_invoice.total = quote.total
                linked_invoice.balance_due = quote.total
                linked_invoice.notes = quote.notes or linked_invoice.notes
                linked_invoice.terms = quote.terms or linked_invoice.terms
                linked_invoice.save(update_fields=[
                    "subtotal", "discount", "tax", "total",
                    "balance_due", "notes", "terms", "updated_at",
                ])

                # Replace line items
                linked_invoice.items.all().delete()
                new_items = [
                    InvoiceItem(
                        invoice=linked_invoice,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        tax_rate=item.tax_rate,
                        discount=item.discount,
                        amount=item.amount,
                    )
                    for item in quote.items.all()
                ]
                if new_items:
                    InvoiceItem.objects.bulk_create(new_items)
        except Exception:
            # Never let a sync failure block the quote update response
            pass
        # ─────────────────────────────────────────────────────────────────

        return Response({
            "success": True,
            "message": "Quote updated successfully.",
            "data": QuoteSerializer(
                quote
            ).data,
        })

    try:
        quote.delete()
    except ProtectedError:
        return Response(
            {"success": False, "message": "This quote has invoices and cannot be deleted."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        status=status.HTTP_204_NO_CONTENT
    )


# ============================================================
# APPROVE / ACCEPT (Admin or Client)
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_quote(request, pk):

    business = get_user_business(
        request.user
    )

    if business:
        quote = get_object_or_404(
            Quote,
            pk=pk,
            business=business,
        )
    else:
        quote = get_object_or_404(
            Quote,
            pk=pk,
            client__email__iexact=request.user.email,
        )

    quote.status = Quote.Status.ACCEPTED
    quote.save()

    return Response({
        "success": True,
        "message": "Quote approved successfully.",
        "data": QuoteSerializer(
            quote
        ).data,
    })


# ============================================================
# REJECT / DECLINE (Admin or Client)
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_quote(request, pk):

    business = get_user_business(
        request.user
    )

    if business:
        quote = get_object_or_404(
            Quote,
            pk=pk,
            business=business,
        )
    else:
        quote = get_object_or_404(
            Quote,
            pk=pk,
            client__email__iexact=request.user.email,
        )

    quote.status = Quote.Status.REJECTED
    quote.save()

    return Response({
        "success": True,
        "message": "Quote rejected successfully.",
        "data": QuoteSerializer(
            quote
        ).data,
    })


# ============================================================
# CONVERT TO INVOICE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def convert_to_invoice(request, pk):
    business = get_user_business(
        request.user
    )

    with transaction.atomic():
        quote = get_object_or_404(
            Quote.objects.select_related("client").prefetch_related("items"),
            pk=pk,
            business=business,
        )

        if quote.status == Quote.Status.CONVERTED:
            return Response(
                {
                    "success": False,
                    "message": "Quote is already converted to an invoice.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        app_settings = AppSettings.objects.select_for_update().get_or_create(
            business=business
        )[0]

        invoice_number = (
            f"{app_settings.invoice_prefix}-"
            f"{app_settings.next_invoice_number:04d}"
        )

        app_settings.next_invoice_number += 1
        app_settings.save(update_fields=["next_invoice_number", "updated_at"])

        issue_date = timezone.now().date()
        due_date = issue_date + timedelta(days=app_settings.invoice_due_days)

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
            balance_due=quote.total,
            notes=quote.notes or app_settings.invoice_notes,
            terms=quote.terms or app_settings.invoice_terms,
        )

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
            InvoiceItem.objects.bulk_create(invoice_items)

        quote.status = Quote.Status.CONVERTED
        quote.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "success": True,
            "message": "Quote converted to invoice successfully.",
            "data": InvoiceSerializer(invoice).data,
        },
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# SYNC INVOICE FROM UPDATED QUOTE
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_invoice_from_quote(request, pk):
    """
    POST /api/quotes/<pk>/sync-invoice/

    Re-syncs the linked invoice with the latest quote amounts and items.
    Allowed only if the invoice has no payments yet (balance_due == total).
    """
    business = get_user_business(request.user)

    with transaction.atomic():
        quote = get_object_or_404(
            Quote.objects.select_related("client").prefetch_related("items"),
            pk=pk,
            business=business,
        )

        # Find the invoice linked to this quote
        invoice = Invoice.objects.filter(quote=quote, business=business).select_for_update().first()

        if not invoice:
            return Response(
                {"success": False, "message": "No invoice found linked to this quote. Convert the quote to invoice first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Safety check: do not sync if payments have been made
        if invoice.paid_amount > 0:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"Cannot sync — this invoice already has ₹{invoice.paid_amount} paid. "
                        "Edit the invoice directly instead."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Update invoice financials from quote
        invoice.subtotal = quote.subtotal
        invoice.discount = quote.discount
        invoice.tax = quote.tax
        invoice.total = quote.total
        invoice.balance_due = quote.total
        invoice.notes = quote.notes or invoice.notes
        invoice.terms = quote.terms or invoice.terms
        invoice.save(update_fields=[
            "subtotal", "discount", "tax", "total",
            "balance_due", "notes", "terms", "updated_at",
        ])

        # Replace invoice items with updated quote items
        invoice.items.all().delete()
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
            InvoiceItem.objects.bulk_create(invoice_items)

    return Response(
        {
            "success": True,
            "message": f"Invoice {invoice.invoice_number} synced successfully from quote {quote.quote_number}.",
            "data": InvoiceSerializer(invoice).data,
        }
    )


# ============================================================
# PDF GENERATION
# ============================================================

@extend_schema(tags=["Quotes"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quote_pdf(request, pk):
    from django.http import HttpResponse
    from .pdf import generate_quote_pdf

    is_admin = is_admin_user(request.user)
    business = get_user_business(request.user) if is_admin else None

    if is_admin:
        quote = get_object_or_404(
            Quote.objects.select_related("client", "business").prefetch_related("items"),
            pk=pk,
            business=business,
        )
    else:
        quote = get_object_or_404(
            Quote.objects.select_related("client", "business").prefetch_related("items"),
            pk=pk,
            client__email__iexact=request.user.email,
        )

    template_name = request.GET.get("template")
    pdf = generate_quote_pdf(quote, template=template_name)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="quote_{quote.quote_number}.pdf"'
    return response