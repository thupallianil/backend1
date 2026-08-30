from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.models import BusinessProfile, Vendor
from .serializers import VendorSerializer


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


@extend_schema(tags=["Vendors"])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def vendor_list_create(request):
    from api.tenant_helpers import resolve_user_context, get_request_business
    role, user_biz, entity = resolve_user_context(request.user)
    business = user_biz or get_request_business(request)

    if request.method == "GET":
        if role == "SUPER_ADMIN":
            biz_id = request.query_params.get("business_id")
            vendors = Vendor.objects.all()
            if biz_id:
                vendors = vendors.filter(business_id=biz_id)
            vendors = vendors.order_by("-created_at")
        else:
            vendors = Vendor.objects.filter(business=business).order_by("-created_at")

        # Search filter
        search = request.query_params.get("search", "").strip()
        if search:
            vendors = vendors.filter(
                Q(name__icontains=search)
                | Q(company_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(tax_number__icontains=search)
                | Q(category__icontains=search)
                | Q(city__icontains=search)
            )

        # Category filter
        category = request.query_params.get("category", "").strip()
        if category and category.lower() != "all":
            vendors = vendors.filter(category=category)

        # Status filter
        status_param = request.query_params.get("status", "").strip().lower()
        if status_param == "active":
            vendors = vendors.filter(is_active=True)
        elif status_param == "inactive":
            vendors = vendors.filter(is_active=False)

        serializer = VendorSerializer(vendors, many=True)
        return Response({
            "success": True,
            "message": "Vendors retrieved successfully",
            "data": serializer.data,
            "count": vendors.count(),
        })

    # POST - Create Vendor
    serializer = VendorSerializer(data=request.data)
    if serializer.is_valid():
        vendor = serializer.save(business=business)
        return Response(
            {
                "success": True,
                "message": "Vendor created successfully",
                "data": VendorSerializer(vendor).data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "success": False,
            "message": "Validation error",
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(tags=["Vendors"])
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def vendor_detail(request, pk):
    business = get_user_business(request.user)

    if not business:
        return Response(
            {"success": False, "message": "Business profile not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    vendor = get_object_or_404(Vendor, pk=pk, business=business)

    if request.method == "GET":
        serializer = VendorSerializer(vendor)
        return Response({
            "success": True,
            "message": "Vendor retrieved successfully",
            "data": serializer.data,
        })

    if request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"
        serializer = VendorSerializer(vendor, data=request.data, partial=partial)
        if serializer.is_valid():
            updated_vendor = serializer.save()
            return Response({
                "success": True,
                "message": "Vendor updated successfully",
                "data": VendorSerializer(updated_vendor).data,
            })
        return Response(
            {
                "success": False,
                "message": "Validation error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        vendor_name = vendor.company_name or vendor.name
        vendor.delete()
        return Response({
            "success": True,
            "message": f"Vendor '{vendor_name}' deleted successfully",
        })


@extend_schema(tags=["Vendors"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def vendor_stats(request):
    business = get_user_business(request.user)

    if not business:
        return Response({
            "success": True,
            "data": {
                "total_vendors": 0,
                "active_vendors": 0,
                "inactive_vendors": 0,
                "tax_registered": 0,
                "categories": {},
            },
        })

    vendors = Vendor.objects.filter(business=business)
    total_vendors = vendors.count()
    active_vendors = vendors.filter(is_active=True).count()
    inactive_vendors = vendors.filter(is_active=False).count()
    tax_registered = vendors.exclude(tax_number="").count()

    # Category breakdown
    categories_qs = (
        vendors.values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    categories = {item["category"]: item["count"] for item in categories_qs}

    return Response({
        "success": True,
        "data": {
            "total_vendors": total_vendors,
            "active_vendors": active_vendors,
            "inactive_vendors": inactive_vendors,
            "tax_registered": tax_registered,
            "categories": categories,
        },
    })
