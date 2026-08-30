from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import (
    Vendor,
    BusinessProfile,
    Invoice,
    Quote,
    Payment,
    Ticket,
    TicketMessage,
    Task,
    Deliverable,
)
from api.vendors.serializers import VendorSerializer


def get_vendor_for_user(user):
    """
    Finds the active Vendor record linked to the given user or matching email.
    """
    vendor = Vendor.objects.filter(Q(user=user) | Q(email__iexact=user.email)).first()
    if not vendor:
        default_biz = BusinessProfile.objects.first()
        if default_biz:
            vendor = Vendor.objects.create(
                business=default_biz,
                name=user.get_full_name() or user.username,
                company_name=f"{user.username} Enterprises",
                email=user.email,
                user=user,
            )
    return vendor


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_dashboard(request):
    """
    Returns high-level operational statistics for the logged-in vendor.
    """
    vendor = get_vendor_for_user(request.user)
    if not vendor:
        return Response({
            "success": True,
            "data": {
                "metrics": {
                    "total_orders": 0,
                    "active_contracts": 0,
                    "total_receivables": 0.0,
                    "paid_amount": 0.0,
                },
                "vendor": None,
                "recent_orders": [],
                "stats": {
                    "rfqs": {"value": 0, "subtext": "Received this month"},
                    "submitted_quotes": {"value": 0, "subtext": "This month"},
                    "approved_quotes": {"value": 0, "subtext": "This month"},
                    "purchase_orders": {"value": 0, "subtext": "Active orders"},
                    "total_invoice_amount": {"value": "₹0.00", "raw": 0, "subtext": "This month"},
                },
                "quotation_status": {
                    "total": 0,
                    "breakdown": [],
                },
                "recent_rfqs": [],
                "quotation_trend": [],
                "recent_quotations": [],
                "purchase_orders": [],
                "recent_payments": [],
                "recent_activities": [],
            }
        })

    tasks = Task.objects.filter(assigned_vendor=vendor)
    delivs = Deliverable.objects.filter(Q(task__assigned_vendor=vendor) | Q(submitted_by=request.user))
    
    # Quotes and invoices
    quotes_qs = Quote.objects.filter(business=vendor.business) if vendor.business else Quote.objects.none()
    invoices_qs = Invoice.objects.filter(business=vendor.business) if vendor.business else Invoice.objects.none()
    payments_qs = Payment.objects.filter(invoice__business=vendor.business) if vendor.business else Payment.objects.none()

    total_tasks = tasks.count()
    active_tasks = tasks.filter(status__in=["pending", "in_progress"]).count()
    submitted_delivs = delivs.count()
    approved_delivs = delivs.filter(status__in=["admin_approved", "client_approved"]).count()
    total_inv_amount = invoices_qs.aggregate(total=Sum("total"))["total"] or 0

    return Response({
        "success": True,
        "data": {
            "vendor": VendorSerializer(vendor).data,
            "vendor_name": vendor.company_name or vendor.name,
            "stats": {
                "rfqs": {"value": total_tasks, "subtext": "Assigned tasks"},
                "submitted_quotes": {"value": submitted_delivs, "subtext": "Deliverables submitted"},
                "approved_quotes": {"value": approved_delivs, "subtext": "Approved deliverables"},
                "purchase_orders": {"value": active_tasks, "subtext": "Active task orders"},
                "total_invoice_amount": {"value": f"₹{total_inv_amount:,.2f}", "raw": float(total_inv_amount), "subtext": "Invoiced work"},
            },
            "quotation_status": {
                "total": total_tasks,
                "breakdown": [
                    {"name": "Pending", "value": tasks.filter(status="pending").count(), "percentage": 0, "color": "#F59E0B"},
                    {"name": "In Progress", "value": tasks.filter(status="in_progress").count(), "percentage": 0, "color": "#3B82F6"},
                    {"name": "Completed", "value": tasks.filter(status="completed").count(), "percentage": 0, "color": "#10B981"},
                ],
            },
            "recent_rfqs": [
                {
                    "id": t.id,
                    "rfq_no": f"TSK-{t.id}",
                    "product_service": t.title,
                    "qty": 1,
                    "deadline": str(t.due_date or "-"),
                }
                for t in tasks.order_by("-created_at")[:5]
            ],
            "quotation_trend": [],
            "recent_quotations": [
                {
                    "id": d.id,
                    "quote_no": f"DELIV-{d.id}",
                    "rfq_no": f"TSK-{d.task_id}" if d.task_id else "-",
                    "client": d.project.title if d.project else "-",
                    "amount": f"{d.version}",
                    "status": d.status.replace("_", " ").title(),
                    "submitted_on": str(d.submitted_at.date()) if d.submitted_at else str(d.created_at.date()),
                }
                for d in delivs.order_by("-created_at")[:5]
            ],
            "purchase_orders": [
                {
                    "id": t.id,
                    "po_no": f"PO-TASK-{t.id}",
                    "client": t.project.title if t.project else "-",
                    "amount": f"₹{t.estimated_hours * 100:,.2f}" if t.estimated_hours else "₹0.00",
                    "status": t.status.replace("_", " ").title(),
                    "delivery_date": str(t.due_date or "-"),
                }
                for t in tasks.order_by("-created_at")[:5]
            ],
            "recent_payments": [
                {
                    "id": p.id,
                    "invoice_no": p.invoice.invoice_number if p.invoice else f"PAY-{p.id}",
                    "amount": f"₹{p.amount:,.2f}",
                    "status": p.status.title(),
                    "paid_on": str(p.created_at.date()),
                }
                for p in payments_qs.order_by("-created_at")[:5]
            ],
            "recent_activities": [],
        }
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_orders(request):
    """
    Returns list of purchase orders and deliverables for the vendor.
    """
    vendor = get_vendor_for_user(request.user)
    if not vendor:
        return Response({"success": True, "data": [], "count": 0})

    tasks = Task.objects.filter(assigned_vendor=vendor).select_related("project")
    orders = [
        {
            "id": f"TSK-{t.id}",
            "order_number": f"PO-TASK-{t.id}",
            "title": t.title,
            "client_name": t.project.title if t.project else "Assigned Project",
            "issue_date": str(t.created_at.date()),
            "due_date": str(t.due_date) if t.due_date else "-",
            "status": t.status.replace("_", " ").title(),
            "items_count": 1,
            "total_amount": float(t.estimated_hours or 0) * 100.0,
            "currency": "INR",
        }
        for t in tasks.order_by("-created_at")
    ]

    return Response({
        "success": True,
        "data": orders,
        "count": len(orders),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_invoices(request):
    """
    Returns invoices/bills submitted by the vendor.
    """
    vendor = get_vendor_for_user(request.user)
    if not vendor or not vendor.business:
        return Response({"success": True, "data": [], "count": 0})

    invoices_qs = Invoice.objects.filter(business=vendor.business)
    invoices = [
        {
            "id": f"INV-{i.id}",
            "invoice_number": i.invoice_number,
            "po_reference": f"INV-{i.id}",
            "billed_to": vendor.business.business_name,
            "issue_date": str(i.issue_date or i.created_at.date()),
            "due_date": str(i.due_date or "-"),
            "status": i.status.replace("_", " ").title(),
            "amount": float(i.total),
            "paid_amount": float(i.paid_amount),
        }
        for i in invoices_qs.order_by("-created_at")
    ]

    return Response({
        "success": True,
        "data": invoices,
        "count": len(invoices),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_payments(request):
    """
    Returns payouts and remittance records received by the vendor.
    """
    vendor = get_vendor_for_user(request.user)
    if not vendor or not vendor.business:
        return Response({"success": True, "data": [], "count": 0})

    payments_qs = Payment.objects.filter(invoice__business=vendor.business)
    payments = [
        {
            "id": f"PAY-{p.id}",
            "payment_number": f"PAY-{p.id}",
            "invoice_number": p.invoice.invoice_number if p.invoice else "-",
            "payment_date": str(p.created_at.date()),
            "method": p.method or "Online Transfer",
            "reference": p.transaction_id or "-",
            "amount": float(p.amount),
            "status": p.status.title(),
        }
        for p in payments_qs.order_by("-created_at")
    ]

    return Response({
        "success": True,
        "data": payments,
        "count": len(payments),
    })

    return Response({
        "success": True,
        "data": payments,
        "count": len(payments),
    })


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def vendor_profile(request):
    """
    View and update Vendor profile details, bank accounts, and tax registrations.
    """
    vendor = get_vendor_for_user(request.user)
    if not vendor:
        return Response({"success": False, "message": "Vendor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({
            "success": True,
            "data": VendorSerializer(vendor).data,
        })

    elif request.method in ["PUT", "PATCH"]:
        serializer = VendorSerializer(vendor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "message": "Vendor profile updated successfully.",
                "data": serializer.data,
            })
        return Response({
            "success": False,
            "errors": serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)
