from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from api.models import AuditLog
from api.tenant_helpers import resolve_user_context
from .serializers import AuditLogSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_log_list(request):
    role, user_biz, _ = resolve_user_context(request.user)

    if role == "SUPER_ADMIN":
        qs = AuditLog.objects.all()
        biz_id = request.query_params.get("business_id")
        if biz_id:
            qs = qs.filter(business_id=biz_id)
    elif role == "ADMIN":
        if not user_biz:
            return Response([], status=status.HTTP_200_OK)
        qs = AuditLog.objects.filter(business=user_biz)
    else:
        return Response({"error": "Only admins can view audit logs"}, status=status.HTTP_403_FORBIDDEN)

    action_filter = request.query_params.get("action")
    if action_filter:
        qs = qs.filter(action__icontains=action_filter)

    entity_filter = request.query_params.get("entity_type")
    if entity_filter:
        qs = qs.filter(entity_type__icontains=entity_filter)

    search = request.query_params.get("search")
    if search:
        qs = qs.filter(
            Q(action__icontains=search) |
            Q(details__icontains=search) |
            Q(actor_role__icontains=search) |
            Q(actor__username__icontains=search)
        )

    # Limit to latest 100
    serializer = AuditLogSerializer(qs.order_by("-created_at")[:100], many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
