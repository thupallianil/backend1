from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.models import Notification
from .serializers import NotificationSerializer


@extend_schema(tags=["Notifications"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:50]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response({
        "success": True,
        "unread_count": unread_count,
        "data": serializer.data,
    })


@extend_schema(tags=["Notifications"])
@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def notification_detail(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)

    if request.method == "PATCH":
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        return Response({
            "success": True,
            "message": "Notification marked as read.",
            "data": NotificationSerializer(notification).data,
        })

    if request.method == "DELETE":
        notification.delete()
        return Response({
            "success": True,
            "message": "Notification deleted.",
        })


@extend_schema(tags=["Notifications"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({
        "success": True,
        "message": "All notifications marked as read.",
    })
