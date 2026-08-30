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
    AuditLog,
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
        return Response({
            "success": True,
            "data": {
                "quotes": {"total": 0, "pending": 0, "under_review": 0, "approved": 0, "rejected": 0},
                "invoices": {"total": 0, "draft": 0, "under_review": 0, "approved": 0, "paid": 0},
                "stats": {
                    "total_clients": 0,
                    "total_vendors": 0,
                    "total_revenue": 0.0,
                    "total_invoices": 0,
                    "total_quotes": 0,
                    "total_deliverables": 0,
                    "approved_deliverables": 0,
                    "pending_deliverables": 0,
                },
                "recent_quotes": [],
                "recent_invoices": [],
                "recent_activities": [],
                "chart_data": {
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "revenue": [0, 0, 0, 0, 0, 0],
                    "invoices": [0, 0, 0, 0, 0, 0],
                    "quotes": [0, 0, 0, 0, 0, 0],
                },
            }
        })

    invoices = Invoice.objects.filter(
        business=business
    )

    payments = Payment.objects.filter(
        business=business
    )

    # Calculate quote counts and statuses
    quotes = Quote.objects.filter(business=business)
    quotes_count = quotes.count()
    quotes_pending = quotes.filter(status__in=[Quote.Status.DRAFT, Quote.Status.SENT]).count()
    quotes_under_review = quotes.filter(status=Quote.Status.SENT).count()
    quotes_approved = quotes.filter(status=Quote.Status.ACCEPTED).count()
    quotes_rejected = quotes.filter(status=Quote.Status.REJECTED).count()

    # Calculate invoice counts and statuses
    invoices_count = invoices.count()
    inv_draft = invoices.filter(status=Invoice.Status.DRAFT).count()
    inv_under_review = invoices.filter(status__in=[Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID]).count()
    inv_approved = invoices.filter(status=Invoice.Status.SENT).count()
    inv_paid = invoices.filter(status=Invoice.Status.PAID).count()

    total_revenue_val = (
        payments.filter(status=Payment.Status.SUCCESS).aggregate(total=Sum("amount"))["total"] or 0
    )

    clients_count = Client.objects.filter(business=business).count()
    vendors_count = Vendor.objects.filter(business=business).count()

    # Dynamic recent activities from audit log
    recent_activities_qs = AuditLog.objects.filter(business=business).order_by("-created_at")[:6]
    recent_activities = [
        {
            "id": a.id,
            "type": a.action.lower(),
            "title": a.action.replace("_", " ").title(),
            "subtitle": a.details or f"By {a.actor.username if a.actor else 'Admin'}",
            "time": a.created_at.strftime("%b %d, %H:%M") if a.created_at else "Recently",
            "color": "purple",
        }
        for a in recent_activities_qs
    ]

    total_q_safe = quotes_count if quotes_count > 0 else 1
    total_i_safe = invoices_count if invoices_count > 0 else 1

    return Response({
        "success": True,
        "data": {
            "clients": clients_count,
            "vendors": vendors_count,
            "active_vendors": Vendor.objects.filter(business=business, is_active=True).count(),
            "quotations": quotes_count,
            "invoices": invoices_count,
            "paid_invoices": inv_paid,
            "pending_invoices": inv_under_review,
            "overdue_invoices": invoices.filter(status=Invoice.Status.OVERDUE).count(),
            "total_revenue": total_revenue_val,
            "pending_amount": invoices.aggregate(total=Sum("balance_due"))["total"] or 0,
            
            # Stat Cards
            "stats": {
                "clients": {"value": clients_count, "growth": "+0.0%", "from": "from last month"},
                "vendors": {"value": vendors_count, "growth": "+0.0%", "from": "from last month"},
                "quotations": {"value": quotes_count, "growth": "+0.0%", "from": "from last month"},
                "invoices": {"value": invoices_count, "growth": "+0.0%", "from": "from last month"},
                "revenue": {"value": f"₹{total_revenue_val:,.2f}", "raw": total_revenue_val, "growth": "+0.0%", "from": "from last month"},
            },

            # Quotations Status Breakdown (Donut Chart)
            "quotations_by_status": {
                "total": quotes_count,
                "breakdown": [
                    {"name": "Pending", "value": quotes_pending, "color": "#F59E0B", "percentage": round((quotes_pending / total_q_safe) * 100, 1)},
                    {"name": "Under Review", "value": quotes_under_review, "color": "#3B82F6", "percentage": round((quotes_under_review / total_q_safe) * 100, 1)},
                    {"name": "Approved", "value": quotes_approved, "color": "#10B981", "percentage": round((quotes_approved / total_q_safe) * 100, 1)},
                    {"name": "Rejected", "value": quotes_rejected, "color": "#EF4444", "percentage": round((quotes_rejected / total_q_safe) * 100, 1)},
                ]
            },

            # Invoices Status Breakdown (Donut Chart)
            "invoices_by_status": {
                "total": invoices_count,
                "breakdown": [
                    {"name": "Draft", "value": inv_draft, "color": "#F59E0B", "percentage": round((inv_draft / total_i_safe) * 100, 1)},
                    {"name": "Under Review", "value": inv_under_review, "color": "#3B82F6", "percentage": round((inv_under_review / total_i_safe) * 100, 1)},
                    {"name": "Approved", "value": inv_approved, "color": "#10B981", "percentage": round((inv_approved / total_i_safe) * 100, 1)},
                    {"name": "Paid", "value": inv_paid, "color": "#8B5CF6", "percentage": round((inv_paid / total_i_safe) * 100, 1)},
                ]
            },

            # Quotation & Invoice Overview
            "overview_chart": [],

            # Recent Quotations Table
            "recent_quotations": [
                {
                    "id": q.id,
                    "quote_number": q.quote_number,
                    "client": q.client.name if q.client else "Client",
                    "vendor": getattr(q, "vendor_name", "-") or "-",
                    "amount": f"₹{int(q.total):,}" if q.total else "₹0",
                    "status": "Pending" if q.status == Quote.Status.DRAFT else ("Under Review" if q.status == Quote.Status.SENT else ("Approved" if q.status == Quote.Status.ACCEPTED else "Rejected")),
                    "date": str(q.issue_date or ""),
                }
                for q in quotes.order_by("-created_at")[:5]
            ],

            # Recent Invoices Table
            "recent_invoices": [
                {
                    "id": i.id,
                    "invoice_number": i.invoice_number,
                    "client": i.client.name if i.client else "Client",
                    "amount": f"₹{int(i.total):,}" if i.total else "₹0",
                    "status": "Paid" if i.status == Invoice.Status.PAID else ("Partially Paid" if i.status == Invoice.Status.PARTIALLY_PAID else ("Sent" if i.status == Invoice.Status.SENT else ("Overdue" if i.status == Invoice.Status.OVERDUE else "Draft"))),
                    "date": str(i.issue_date or ""),
                }
                for i in invoices.order_by("-created_at")[:5]
            ],

            # Recent Activity Timeline Feed
            "recent_activities": recent_activities,
            
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