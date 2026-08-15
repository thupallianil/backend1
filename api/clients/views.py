from django.shortcuts import get_object_or_404
from django.db.models.deletion import ProtectedError

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import BusinessProfile, Client
from drf_spectacular.utils import extend_schema
from .serializers import ClientSerializer


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


@extend_schema(tags=["Clients"])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def client_list_create(request):
    business = get_user_business(request.user)

    if request.method == "GET":
        if business:
            clients = Client.objects.filter(
                business=business
            ).order_by("-created_at")
        else:
            clients = Client.objects.filter(
                email__iexact=request.user.email
            ).order_by("-created_at")

        serializer = ClientSerializer(
            clients,
            many=True,
        )

        return Response({
            "success": True,
            "message": "Clients retrieved successfully",
            "data": serializer.data,
        })

    serializer = ClientSerializer(
        data=request.data
    )

    if serializer.is_valid():
        client = serializer.save(
            business=business
        )

        return Response(
            {
                "success": True,
                "message": "Client created successfully",
                "data": ClientSerializer(client).data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "success": False,
            "message": "Client creation failed",
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(tags=["Clients"])
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def client_detail(request, pk):
    business = get_user_business(request.user)

    if business:
        client = get_object_or_404(
            Client,
            pk=pk,
            business=business,
        )
    else:
        client = get_object_or_404(
            Client,
            pk=pk,
            email__iexact=request.user.email,
        )

    if request.method == "GET":
        serializer = ClientSerializer(client)

        return Response({
            "success": True,
            "message": "Client retrieved successfully",
            "data": serializer.data,
        })

    if request.method in ["PUT", "PATCH"]:
        serializer = ClientSerializer(
            client,
            data=request.data,
            partial=request.method == "PATCH",
        )

        if serializer.is_valid():
            serializer.save()

            return Response({
                "success": True,
                "message": "Client updated successfully",
                "data": serializer.data,
            })

        return Response(
            {
                "success": False,
                "message": "Client update failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        client.delete()
    except ProtectedError:
        return Response(
            {"success": False, "message": "This client has invoices or quotes and cannot be deleted."},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "success": True,
            "message": "Client deleted successfully",
        },
        status=status.HTTP_204_NO_CONTENT,
    )
