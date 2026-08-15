import random
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.models import (
    BusinessProfile,
    Client,
    Ticket,
    TicketMessage,
    Notification,
)
from .serializers import TicketSerializer, TicketMessageSerializer

User = get_user_model()


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


def get_or_create_business(user):
    biz = get_user_business(user)
    if not biz:
        biz, _ = BusinessProfile.objects.get_or_create(
            owner=user,
            defaults={"business_name": f"{user.username}'s Business"},
        )
    return biz


def generate_ticket_number(business):
    year = timezone.now().strftime("%Y")
    count = Ticket.objects.filter(business=business).count() + 1
    rand_part = random.randint(100, 999)
    return f"TCK-{year}-{count:04d}-{rand_part}"


# ============================================================
# TICKETS LIST & CREATE
# ============================================================

@extend_schema(tags=["Tickets"])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ticket_list(request):
    user = request.user
    role = getattr(user, "role", "").upper()

    if request.method == "GET":
        if role == "CLIENT":
            # Filter tickets where client matches user's email
            tickets = Ticket.objects.filter(
                client__email__iexact=user.email
            ).select_related("client", "business", "created_by").prefetch_related("messages")
        else:
            # Admin view: all tickets for business
            business = get_or_create_business(user)
            tickets = Ticket.objects.filter(
                business=business
            ).select_related("client", "business", "created_by").prefetch_related("messages")

        # Query filters
        status_filter = request.query_params.get("status")
        if status_filter and status_filter != "all":
            tickets = tickets.filter(status=status_filter)

        priority_filter = request.query_params.get("priority")
        if priority_filter and priority_filter != "all":
            tickets = tickets.filter(priority=priority_filter)

        category_filter = request.query_params.get("category")
        if category_filter and category_filter != "all":
            tickets = tickets.filter(category=category_filter)

        search = request.query_params.get("search", "").strip()
        if search:
            tickets = tickets.filter(
                Q(ticket_number__icontains=search)
                | Q(subject__icontains=search)
                | Q(description__icontains=search)
                | Q(client__name__icontains=search)
                | Q(client__email__icontains=search)
            )

        serializer = TicketSerializer(tickets, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
        })

    # -------------------------------------------------------- POST (Create Ticket)
    data = request.data.copy()
    subject = str(data.get("subject") or "").strip()
    description = str(data.get("description") or "").strip()
    category = str(data.get("category") or "general").strip()
    priority = str(data.get("priority") or "medium").strip()
    attachment = request.FILES.get("attachment") or None

    if not subject:
        return Response({
            "success": False,
            "message": "Subject is required.",
        }, status=status.HTTP_400_BAD_REQUEST)

    if not description:
        return Response({
            "success": False,
            "message": "Description is required.",
        }, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        if role == "CLIENT":
            # Find matching client record for this user
            client = Client.objects.filter(email__iexact=user.email).first()
            if not client:
                # Find default business or first active business
                business = BusinessProfile.objects.first()
                if not business:
                    owner_user = User.objects.filter(is_staff=True).first() or user
                    business = get_or_create_business(owner_user)
                client = Client.objects.create(
                    business=business,
                    name=user.get_full_name() or user.username or "Client User",
                    email=user.email,
                )
            else:
                business = client.business
        else:
            business = get_or_create_business(user)
            client_id = data.get("client") or data.get("client_id")
            if client_id:
                client = get_object_or_404(Client, id=client_id, business=business)
            else:
                client = Client.objects.filter(business=business).first()
                if not client:
                    client = Client.objects.create(
                        business=business,
                        name="General Client",
                        email=user.email,
                    )

        ticket_number = generate_ticket_number(business)

        ticket = Ticket.objects.create(
            business=business,
            client=client,
            created_by=user,
            ticket_number=ticket_number,
            subject=subject,
            category=category,
            priority=priority,
            status=Ticket.Status.OPEN,
            description=description,
            attachment=attachment,
            last_reply_at=timezone.now(),
        )

        # Notify the Admin / Business Owner
        admin_user = business.owner
        if admin_user and admin_user != user:
            Notification.objects.create(
                user=admin_user,
                business=business,
                title=f"New Ticket #{ticket_number}",
                message=f"New support ticket raised by {client.name}: \"{subject}\"",
                type="ticket_raised",
                link=f"/admin/tickets/{ticket.id}",
            )

        serializer = TicketSerializer(ticket)
        return Response({
            "success": True,
            "message": f"Support ticket #{ticket_number} created successfully.",
            "data": serializer.data,
        }, status=status.HTTP_201_CREATED)


# ============================================================
# TICKET DETAIL & UPDATE
# ============================================================

@extend_schema(tags=["Tickets"])
@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def ticket_detail(request, pk):
    user = request.user
    role = getattr(user, "role", "").upper()

    if role == "CLIENT":
        ticket = get_object_or_404(
            Ticket.objects.select_related("client", "business", "created_by").prefetch_related("messages"),
            pk=pk,
            client__email__iexact=user.email,
        )
    else:
        business = get_or_create_business(user)
        ticket = get_object_or_404(
            Ticket.objects.select_related("client", "business", "created_by").prefetch_related("messages"),
            pk=pk,
            business=business,
        )

    # -------------------------------------------------------- GET
    if request.method == "GET":
        serializer = TicketSerializer(ticket)
        return Response({
            "success": True,
            "data": serializer.data,
        })

    # -------------------------------------------------------- PATCH
    if request.method == "PATCH":
        old_status = ticket.status
        data = request.data

        if "status" in data:
            new_status = str(data["status"]).lower().strip()
            ticket.status = new_status

        if "priority" in data:
            ticket.priority = str(data["priority"]).lower().strip()

        if "category" in data:
            ticket.category = str(data["category"]).lower().strip()

        ticket.save()

        # If status changed by Admin, notify the Client
        if role != "CLIENT" and "status" in data and old_status != ticket.status:
            client_user = User.objects.filter(email__iexact=ticket.client.email).first()
            if client_user:
                status_label = ticket.status.replace("_", " ").title()
                Notification.objects.create(
                    user=client_user,
                    business=ticket.business,
                    title=f"Ticket #{ticket.ticket_number} Status Updated",
                    message=f"Your ticket '{ticket.subject}' status is now marked as {status_label}.",
                    type="ticket_status",
                    link=f"/client/tickets/{ticket.id}",
                )

        serializer = TicketSerializer(ticket)
        return Response({
            "success": True,
            "message": "Ticket updated successfully.",
            "data": serializer.data,
        })

    # -------------------------------------------------------- DELETE
    if request.method == "DELETE":
        if role == "CLIENT":
            return Response({
                "success": False,
                "message": "Only administrators can delete tickets.",
            }, status=status.HTTP_403_FORBIDDEN)

        ticket.delete()
        return Response({
            "success": True,
            "message": "Ticket deleted successfully.",
        })


# ============================================================
# TICKET REPLY (MESSAGES)
# ============================================================

@extend_schema(tags=["Tickets"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ticket_reply(request, pk):
    user = request.user
    role = getattr(user, "role", "").upper()

    if role == "CLIENT":
        ticket = get_object_or_404(Ticket, pk=pk, client__email__iexact=user.email)
        sender_role = "client"
    else:
        business = get_or_create_business(user)
        ticket = get_object_or_404(Ticket, pk=pk, business=business)
        sender_role = "admin"

    message_text = str(request.data.get("message") or "").strip()
    attachment = request.FILES.get("attachment") or None

    if not message_text:
        return Response({
            "success": False,
            "message": "Reply message cannot be empty.",
        }, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        msg = TicketMessage.objects.create(
            ticket=ticket,
            sender=user,
            sender_role=sender_role,
            message=message_text,
            attachment=attachment,
        )

        ticket.last_reply_at = timezone.now()

        # Update status based on who replied
        if sender_role == "admin":
            if ticket.status == Ticket.Status.OPEN:
                ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save()

            # Notify Client
            client_user = User.objects.filter(email__iexact=ticket.client.email).first()
            if client_user:
                snippet = message_text[:60] + ("..." if len(message_text) > 60 else "")
                Notification.objects.create(
                    user=client_user,
                    business=ticket.business,
                    title=f"Support Reply: #{ticket.ticket_number}",
                    message=f"Support team replied to '{ticket.subject}': \"{snippet}\"",
                    type="ticket_reply",
                    link=f"/client/tickets/{ticket.id}",
                )
        else:
            # Client replied
            if ticket.status in [Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.WAITING_CLIENT]:
                ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save()

            # Notify Admin / Business Owner
            admin_user = ticket.business.owner
            if admin_user and admin_user != user:
                snippet = message_text[:60] + ("..." if len(message_text) > 60 else "")
                Notification.objects.create(
                    user=admin_user,
                    business=ticket.business,
                    title=f"Client Reply: #{ticket.ticket_number}",
                    message=f"{ticket.client.name} replied on '{ticket.subject}': \"{snippet}\"",
                    type="ticket_reply",
                    link=f"/admin/tickets/{ticket.id}",
                )

        # Return refreshed ticket
        ticket.refresh_from_db()
        serializer = TicketSerializer(ticket)
        return Response({
            "success": True,
            "message": "Reply posted successfully.",
            "data": serializer.data,
        }, status=status.HTTP_201_CREATED)
