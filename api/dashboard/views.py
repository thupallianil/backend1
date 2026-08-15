from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import (
    BusinessProfile,
    Client,
    Invoice,
    Payment,
    Quote,
)
from api.reports.services import ReportService

def get_business(user):
    return get_object_or_404(
        BusinessProfile,
        owner=user,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    business = get_business(request.user)

    invoices = Invoice.objects.filter(
        business=business
    )

    payments = Payment.objects.filter(
        business=business
    )

    return Response({
        "success": True,
        "data": {
            "clients": Client.objects.filter(
                business=business
            ).count(),

            "invoices": invoices.count(),

            "paid_invoices": invoices.filter(
                status=Invoice.Status.PAID
            ).count(),

            "pending_invoices": invoices.filter(
                status__in=[
                    Invoice.Status.SENT,
                    Invoice.Status.PARTIALLY_PAID,
                ]
            ).count(),

            "overdue_invoices": invoices.filter(
                status=Invoice.Status.OVERDUE
            ).count(),

            "total_revenue": (
                payments.filter(
                    status=Payment.Status.SUCCESS
                ).aggregate(
                    total=Sum("amount")
                )["total"] or 0
            ),

            "pending_amount": (
                invoices.aggregate(
                    total=Sum("balance_due")
                )["total"] or 0
            ),

            "recent_clients": [
                {
                    "id": c.id,
                    "name": c.name,
                    "company_name": c.company_name,
                    "email": c.email,
                    "invoice_count": Invoice.objects.filter(client=c).count(),
                    "outstanding": Invoice.objects.filter(client=c).exclude(status=Invoice.Status.PAID).aggregate(total=Sum("balance_due"))["total"] or 0,
                }
                for c in Client.objects.filter(business=business).order_by("-created_at")[:5]
            ],

            "recent_invoices": [
                {
                    "id": i.id,
                    "invoice_number": i.invoice_number,
                    "client": i.client.name,
                    "total": i.total,
                    "status": i.status,
                    "issue_date": i.issue_date,
                    "due_date": i.due_date,
                }
                for i in invoices.order_by("-created_at")[:5]
            ],

            "recent_payments": [
                {
                    "id": p.id,
                    "invoice": p.invoice.invoice_number,
                    "amount": p.amount,
                    "method": p.method,
                    "status": p.status,
                    "created_at": p.created_at,
                }
                for p in payments.order_by("-created_at")[:5]
            ],
            
            "revenue_chart": [
                {
                    "month": m["month"],
                    "revenue": m["sales"],
                }
                for m in ReportService.sales(request.user).get("months", [])
            ],
            
            "payment_chart": ReportService.payments(request.user).get("months", []),
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    return dashboard(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_invoices(request):
    business = get_business(request.user)

    invoices = Invoice.objects.filter(
        business=business
    ).order_by("-created_at")[:10]

    data = [
        {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "client": invoice.client.name,
            "total": invoice.total,
            "status": invoice.status,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
        }
        for invoice in invoices
    ]

    return Response({
        "success": True,
        "data": data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recent_payments(request):
    business = get_business(request.user)

    payments = Payment.objects.filter(
        business=business
    ).order_by("-created_at")[:10]

    data = [
        {
            "id": payment.id,
            "invoice": payment.invoice.invoice_number,
            "amount": payment.amount,
            "method": payment.method,
            "status": payment.status,
            "created_at": payment.created_at,
        }
        for payment in payments
    ]

    return Response({
        "success": True,
        "data": data,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search(request):
    business = get_business(request.user)
    query = request.query_params.get("q", "").strip()

    if not query:
        return Response({"success": True, "data": []})

    clients = Client.objects.filter(
        Q(business=business) &
        (Q(name__icontains=query) | Q(company_name__icontains=query) | Q(email__icontains=query))
    )[:5]

    invoices = Invoice.objects.filter(
        Q(business=business) &
        (Q(invoice_number__icontains=query) | Q(client__name__icontains=query) | Q(client__company_name__icontains=query))
    )[:5]

    quotes = Quote.objects.filter(
        Q(business=business) &
        (Q(quote_number__icontains=query) | Q(client__name__icontains=query) | Q(client__company_name__icontains=query))
    )[:5]

    results = []

    for client in clients:
        results.append({
            "id": client.id,
            "type": "client",
            "title": client.name or client.company_name,
            "subtitle": client.email,
        })

    for invoice in invoices:
        results.append({
            "id": invoice.id,
            "type": "invoice",
            "title": invoice.invoice_number,
            "subtitle": f"Client: {invoice.client.name or invoice.client.company_name}",
        })
        
    for quote in quotes:
        results.append({
            "id": quote.id,
            "type": "quote",
            "title": quote.quote_number,
            "subtitle": f"Client: {quote.client.name or quote.client.company_name}",
        })

    return Response({
        "success": True,
        "data": results,
    })