from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import Response

from rest_framework import status

from drf_spectacular.utils import extend_schema

from .services import ReportService

from .serializers import (
    DashboardReportSerializer,
    SalesReportSerializer,
    PaymentReportSerializer,
    TaxReportSerializer,
    ClientReportSerializer,
    ProfitLossReportSerializer,
)


def get_year(request):
    """
    Optional:
        /api/reports/sales/?year=2026
    """

    value = request.query_params.get("year")

    if not value:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ============================================================
# DASHBOARD
# ============================================================

@extend_schema(
    tags=["Reports"],
    responses=DashboardReportSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):

    try:
        year = get_year(request)

        data = ReportService.dashboard(
            request.user,
            year=year,
        )

        serializer = DashboardReportSerializer(
            data
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    except ValueError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:

        print(
            "Dashboard report error:",
            repr(exc)
        )

        return Response(
            {
                "success": False,
                "message": "Unable to load dashboard report.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# SALES
# ============================================================

@extend_schema(
    tags=["Reports"],
    responses=SalesReportSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales(request):

    try:
        year = get_year(request)

        data = ReportService.sales(
            request.user,
            year=year,
        )

        serializer = SalesReportSerializer(
            data
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    except ValueError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:

        print(
            "Sales report error:",
            repr(exc)
        )

        return Response(
            {
                "success": False,
                "message": "Unable to load sales report.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# PAYMENTS
# ============================================================

@extend_schema(
    tags=["Reports"],
    responses=PaymentReportSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payments(request):

    try:
        year = get_year(request)

        data = ReportService.payments(
            request.user,
            year=year,
        )

        serializer = PaymentReportSerializer(
            data
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    except ValueError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:

        print(
            "Payment report error:",
            repr(exc)
        )

        return Response(
            {
                "success": False,
                "message": "Unable to load payment report.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# TAX
# ============================================================

@extend_schema(
    tags=["Reports"],
    responses=TaxReportSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tax(request):

    try:
        year = get_year(request)

        data = ReportService.tax(
            request.user,
            year=year,
        )

        serializer = TaxReportSerializer(
            data
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    except ValueError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:

        print(
            "Tax report error:",
            repr(exc)
        )

        return Response(
            {
                "success": False,
                "message": "Unable to load tax report.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# CLIENTS
# ============================================================

@extend_schema(
    tags=["Reports"],
    responses=ClientReportSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def clients(request):

    try:
        data = ReportService.clients(
            request.user
        )

        serializer = ClientReportSerializer(
            data
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    except ValueError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:

        print(
            "Client report error:",
            repr(exc)
        )

        return Response(
            {
                "success": False,
                "message": "Unable to load client report.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================
# PROFIT / LOSS
# ============================================================

@extend_schema(
    tags=["Reports"],
    responses=ProfitLossReportSerializer,
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profit_loss(request):

    try:
        year = get_year(request)

        data = ReportService.profit_loss(
            request.user,
            year=year,
        )

        serializer = ProfitLossReportSerializer(
            data
        )

        return Response({
            "success": True,
            "data": serializer.data,
        })

    except ValueError as exc:

        return Response(
            {
                "success": False,
                "message": str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception as exc:

        print(
            "Profit/loss report error:",
            repr(exc)
        )

        return Response(
            {
                "success": False,
                "message": "Unable to load profit/loss report.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )