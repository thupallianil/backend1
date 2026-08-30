from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Q, Count

from api.models import (
    Client,
    Project,
    Task,
    Deliverable,
    DeliverableApproval,
    Invoice,
    Payment,
    Receipt,
    Ticket,
    Document,
)
from api.tenant_helpers import resolve_user_context
from api.projects.serializers import ProjectSerializer
from api.deliverables.serializers import DeliverableSerializer
from api.invoices.serializers import InvoiceSerializer
from api.receipts.serializers import ReceiptSerializer
from api.clients.serializers import ClientSerializer


def get_client_for_user(user):
    client = Client.objects.filter(Q(user=user) | Q(email__iexact=user.email)).first()
    if not client and hasattr(user, "profile") and user.profile.client:
        client = user.profile.client
    return client


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_dashboard(request):
    client = get_client_for_user(request.user)
    if not client:
        return Response({
            "success": True,
            "data": {
                "client": None,
                "stats": {
                    "total_projects": 0,
                    "active_projects": 0,
                    "completed_projects": 0,
                    "pending_approvals": 0,
                    "total_invoices": 0,
                    "unpaid_invoices": 0,
                    "total_invoiced": 0,
                    "total_paid": 0,
                    "outstanding_balance": 0,
                },
                "recent_projects": [],
                "pending_deliverables": [],
                "recent_invoices": [],
            }
        }, status=status.HTTP_200_OK)

    projects = Project.objects.filter(client=client)
    total_projects = projects.count()
    active_projects = projects.filter(status__in=["active", "in_progress", "client_review"]).count()
    completed_projects = projects.filter(status="completed").count()

    deliverables = Deliverable.objects.filter(project__client=client)
    pending_approvals = deliverables.filter(status__in=["admin_approved", "client_review"]).count()

    invoices = Invoice.objects.filter(client=client)
    total_invoiced = invoices.aggregate(s=Sum("total"))["s"] or 0
    total_paid = invoices.aggregate(s=Sum("paid_amount"))["s"] or 0
    outstanding = invoices.aggregate(s=Sum("balance_due"))["s"] or 0

    recent_projects_data = ProjectSerializer(projects.order_by("-created_at")[:5], many=True).data
    pending_deliverables_data = DeliverableSerializer(
        deliverables.filter(status__in=["admin_approved", "client_review"]).order_by("-created_at")[:5],
        many=True
    ).data
    recent_invoices_data = InvoiceSerializer(invoices.order_by("-created_at")[:5], many=True).data

    return Response({
        "success": True,
        "data": {
            "client": ClientSerializer(client).data,
            "stats": {
                "total_projects": total_projects,
                "active_projects": active_projects,
                "completed_projects": completed_projects,
                "pending_approvals": pending_approvals,
                "total_invoices": invoices.count(),
                "unpaid_invoices": invoices.exclude(status=Invoice.Status.PAID).count(),
                "total_invoiced": float(total_invoiced),
                "total_paid": float(total_paid),
                "outstanding_balance": float(outstanding),
            },
            "recent_projects": recent_projects_data,
            "pending_deliverables": pending_deliverables_data,
            "recent_invoices": recent_invoices_data,
        }
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_projects_list(request):
    client = get_client_for_user(request.user)
    if not client:
        return Response([], status=status.HTTP_200_OK)

    projects = Project.objects.filter(client=client).order_by("-created_at")
    return Response(ProjectSerializer(projects, many=True).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_approvals_list(request):
    client = get_client_for_user(request.user)
    if not client:
        return Response([], status=status.HTTP_200_OK)

    deliverables = Deliverable.objects.filter(project__client=client).order_by("-created_at")
    return Response(DeliverableSerializer(deliverables, many=True).data, status=status.HTTP_200_OK)
