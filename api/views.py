from django.http import JsonResponse

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import AllowAny
from rest_framework.response import Response


# ============================================================
# API HOME
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def api_index(request):
    return JsonResponse({
        "success": True,
        "message": "Backend API is running successfully.",
        "data": {
            "health": "/api/health/",
            "auth": "/api/auth/",
            "settings": "/api/settings/",
            "profile": "/api/profile/",
            "clients": "/api/clients/",
            "quotes": "/api/quotes/",
            "invoices": "/api/invoices/",
            "payments": "/api/payments/",
            "receipts": "/api/receipts/",
            "dashboard": "/api/dashboard/",
            "reports": "/api/reports/",
        },
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "success": True,
        "message": "Health check successful.",
        "data": {
            "status": "ok",
        },
    })