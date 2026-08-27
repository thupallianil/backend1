from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import (
    BusinessProfile,
    Client,
    Vendor,
    Invoice,
    Payment,
    Quote,
)
from api.reports.services import ReportService

def is_admin_user(user):
    return bool(user.is_staff or user.is_superuser)


def get_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    is_admin = is_admin_user(request.user)

    if not is_admin:
        # Strictly individual client dashboard
        user_email = request.user.email
        invoices = Invoice.objects.filter(client__email__iexact=user_email)
        payments = Payment.objects.filter(invoice__client__email__iexact=user_email)
        quotes = Quote.objects.filter(client__email__iexact=user_email)

        total_paid = (
            payments.filter(status=Payment.Status.SUCCESS).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        total_pending = (
            invoices.exclude(status=Invoice.Status.PAID).aggregate(
                total=Sum("balance_due")
            )["total"]
            or 0
        )

        return Response({
            "success": True,
            "data": {
                "invoices": invoices.count(),
                "paid_invoices": invoices.filter(status=Invoice.Status.PAID).count(),
                "pending_invoices": invoices.filter(
                    status__in=[Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID]
                ).count(),
                "quotes": quotes.count(),
                "total_paid": total_paid,
                "pending_amount": total_pending,
                "recent_invoices": [
                    {
                        "id": i.id,
                        "invoice_number": i.invoice_number,
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
                        "invoice": p.invoice.invoice_number if p.invoice else "",
                        "amount": p.amount,
                        "method": p.method,
                        "status": p.status,
                        "created_at": p.created_at,
                    }
                    for p in payments.order_by("-created_at")[:5]
                ],
            }
        })

    business = get_business(request.user)
    if not business:
        business = BusinessProfile.objects.create(
            owner=request.user,
            business_name=f"{request.user.username}'s Business",
            email=request.user.email,
        )

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

            "vendors": Vendor.objects.filter(
                business=business
            ).count(),

            "active_vendors": Vendor.objects.filter(
                business=business,
                is_active=True
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
                    "total_billed": (
                        Invoice.objects.filter(client=c).aggregate(total=Sum("total"))["total"] or 0
                    ),
                    "outstanding": (
                        Invoice.objects.filter(client=c)
                        .exclude(status=Invoice.Status.PAID)
                        .aggregate(total=Sum("balance_due"))["total"]
                        or 0
                    ),
                }
                for c in Client.objects.filter(business=business).order_by("-created_at")[:6]
            ],

            "recent_vendors": [
                {
                    "id": v.id,
                    "name": v.name,
                    "company_name": v.company_name or v.name,
                    "email": v.email,
                    "phone": v.phone,
                    "category": v.get_category_display() if hasattr(v, "get_category_display") else "Supplier",
                    "terms": "Net 30",
                    "due_amount": 0,
                }
                for v in Vendor.objects.filter(business=business).order_by("-created_at")[:6]
            ],

            "urgent_items": [
                {
                    "id": f"inv-{i.id}",
                    "type": "overdue_invoice" if i.status == Invoice.Status.OVERDUE else "pending_invoice",
                    "title": f"Invoice: #{i.invoice_number}",
                    "entity": i.client.name if i.client else "Client",
                    "amount": float(i.balance_due or i.total or 0),
                    "days_overdue": 1 if i.status == Invoice.Status.OVERDUE else 0,
                    "status": i.status,
                    "due_date": str(i.due_date) if i.due_date else "",
                    "action_label": "Remind Client",
                    "action_link": f"/admin/invoices/{i.id}",
                }
                for i in invoices.filter(
                    status__in=[Invoice.Status.OVERDUE, Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID]
                ).order_by("-created_at")[:5]
            ] + [
                {
                    "id": f"quo-{q.id}",
                    "type": "pending_quote",
                    "title": f"Quotation: #{q.quote_number}",
                    "entity": q.client.name if q.client else "Client",
                    "amount": float(q.total or 0),
                    "days_overdue": 0,
                    "status": q.status,
                    "due_date": str(q.valid_until) if hasattr(q, "valid_until") and q.valid_until else "",
                    "action_label": "Follow Up",
                    "action_link": f"/admin/quotes/{q.id}",
                }
                for q in Quote.objects.filter(business=business, status=Quote.Status.SENT).order_by("-created_at")[:3]
            ],

            "recent_invoices": [
                {
                    "id": i.id,
                    "invoice_number": i.invoice_number,
                    "client": i.client.name if i.client else "Unknown Client",
                    "total": i.total,
                    "status": i.status,
                    "issue_date": i.issue_date,
                    "due_date": i.due_date,
                }
                for i in invoices.order_by("-created_at")[:6]
            ],

            "recent_payments": [
                {
                    "id": p.id,
                    "invoice": p.invoice.invoice_number if p.invoice else "Direct",
                    "amount": p.amount,
                    "method": p.method,
                    "status": p.status,
                    "created_at": p.created_at,
                }
                for p in payments.order_by("-created_at")[:6]
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

    vendors = Vendor.objects.filter(
        Q(business=business) &
        (Q(name__icontains=query) | Q(company_name__icontains=query) | Q(email__icontains=query) | Q(category__icontains=query))
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

    for vendor in vendors:
        results.append({
            "id": vendor.id,
            "type": "vendor",
            "title": vendor.company_name or vendor.name,
            "subtitle": f"{vendor.get_category_display()} • {vendor.email or vendor.phone or 'Vendor'}",
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