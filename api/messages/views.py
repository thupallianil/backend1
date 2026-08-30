from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import get_user_model

from api.models import Message, Project
from api.tenant_helpers import resolve_user_context, get_request_business
from api.utils_events import send_system_notification
from .serializers import MessageSerializer

User = get_user_model()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def message_list_create(request):
    role, user_biz, entity = resolve_user_context(request.user)

    if request.method == "GET":
        qs = Message.objects.all()
        if role == "SUPER_ADMIN":
            biz_id = request.query_params.get("business_id")
            if biz_id:
                qs = qs.filter(business_id=biz_id)
        elif role == "ADMIN":
            if not user_biz:
                return Response([], status=status.HTTP_200_OK)
            qs = qs.filter(business=user_biz)
        else:
            # Vendor or Client: sees messages sent/received by them or project rooms they are members of
            if role == "VENDOR" and entity:
                qs = qs.filter(
                    Q(sender=request.user) |
                    Q(recipient=request.user) |
                    Q(conversation_type="project_room", project__members__vendor=entity)
                ).distinct()
            elif role == "CLIENT" and entity:
                qs = qs.filter(
                    Q(sender=request.user) |
                    Q(recipient=request.user) |
                    Q(conversation_type="project_room", project__client=entity)
                ).distinct()
            else:
                qs = qs.filter(Q(sender=request.user) | Q(recipient=request.user))

        project_id = request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        conv_type = request.query_params.get("conversation_type")
        if conv_type:
            qs = qs.filter(conversation_type=conv_type)

        recipient_id = request.query_params.get("with_user_id")
        if recipient_id:
            qs = qs.filter(
                (Q(sender=request.user) & Q(recipient_id=recipient_id)) |
                (Q(sender_id=recipient_id) & Q(recipient=request.user))
            )

        serializer = MessageSerializer(qs.order_by("created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        business = user_biz or get_request_business(request)
        if not business:
            return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

        content = request.data.get("content", "").strip()
        if not content and not request.FILES.get("attachment"):
            return Response({"error": "Message content or attachment is required"}, status=status.HTTP_400_BAD_REQUEST)

        project_id = request.data.get("project")
        project = Project.objects.filter(id=project_id).first() if project_id else None

        recipient_id = request.data.get("recipient")
        recipient = User.objects.filter(id=recipient_id).first() if recipient_id else None

        conv_type = request.data.get("conversation_type") or ("project_room" if project else "direct_admin_vendor")

        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            msg = serializer.save(
                business=business,
                sender=request.user,
                recipient=recipient,
                project=project,
                conversation_type=conv_type
            )

            # Notify recipient if direct
            if recipient and recipient != request.user:
                send_system_notification(
                    user=recipient,
                    business=business,
                    title="New Message",
                    message=f"{request.user.get_full_name() or request.user.username}: {content[:60]}",
                    notif_type="message",
                    link="/admin/messages" if role != "ADMIN" else "/client/messages"
                )

            return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_messages_read(request):
    sender_id = request.data.get("sender_id")
    project_id = request.data.get("project_id")

    qs = Message.objects.filter(recipient=request.user, is_read=False)
    if sender_id:
        qs = qs.filter(sender_id=sender_id)
    if project_id:
        qs = qs.filter(project_id=project_id)

    updated_count = qs.update(is_read=True)
    return Response({"marked_read": updated_count}, status=status.HTTP_200_OK)
