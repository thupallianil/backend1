import secrets
import string
import uuid
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import BusinessProfile, Client
from drf_spectacular.utils import extend_schema
from .serializers import ClientSerializer

User = get_user_model()


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


def generate_temp_password():
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"Client#{digits}!"


def sync_client_portal_user(client, raw_password=None, auto_generate=False):
    """
    Ensure the client has a matching User account for portal login.
    """
    if not client.email:
        return None, None

    email = client.email.strip().lower()
    user = User.objects.filter(email__iexact=email).first()
    password_to_set = raw_password

    if not user:
        if not password_to_set:
            if auto_generate:
                password_to_set = generate_temp_password()
            else:
                return None, None

        safe_name = "".join(c for c in client.name if c.isalnum() or c == "_").lower() or "client"
        unique_username = f"{safe_name}_{uuid.uuid4().hex[:6]}"
        user = User.objects.create_user(
            username=unique_username,
            email=email,
            password=password_to_set,
            first_name=client.name,
            is_staff=False,
        )
    else:
        if password_to_set:
            user.set_password(password_to_set)
            if client.name:
                user.first_name = client.name
            user.save()

    return user, password_to_set


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
        raw_password = serializer.validated_data.pop("password", "").strip() if "password" in serializer.validated_data else ""
        create_portal = serializer.validated_data.pop("create_portal_access", True) if "create_portal_access" in serializer.validated_data else True

        client = serializer.save(
            business=business
        )

        generated_pass = None
        if client.email and create_portal:
            _, generated_pass = sync_client_portal_user(
                client,
                raw_password=raw_password or None,
                auto_generate=bool(raw_password or create_portal),
            )

        resp_data = ClientSerializer(client).data
        if generated_pass:
            resp_data["generated_credentials"] = {
                "email": client.email,
                "password": generated_pass,
                "login_url": "/login",
            }

        return Response(
            {
                "success": True,
                "message": "Client created successfully",
                "data": resp_data,
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
            raw_password = serializer.validated_data.pop("password", "").strip() if "password" in serializer.validated_data else ""
            create_portal = serializer.validated_data.pop("create_portal_access", True) if "create_portal_access" in serializer.validated_data else True

            client = serializer.save()

            generated_pass = None
            if client.email and (raw_password or create_portal):
                _, generated_pass = sync_client_portal_user(
                    client,
                    raw_password=raw_password or None,
                    auto_generate=bool(raw_password),
                )

            resp_data = serializer.data
            if generated_pass:
                resp_data["generated_credentials"] = {
                    "email": client.email,
                    "password": generated_pass,
                    "login_url": "/login",
                }

            return Response({
                "success": True,
                "message": "Client updated successfully",
                "data": resp_data,
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


@extend_schema(tags=["Clients"])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def client_portal_credentials(request, pk):
    business = get_user_business(request.user)
    if business:
        client = get_object_or_404(Client, pk=pk, business=business)
    else:
        client = get_object_or_404(Client, pk=pk, email__iexact=request.user.email)

    if request.method == "GET":
        user_exists = User.objects.filter(email__iexact=client.email).exists() if client.email else False
        return Response({
            "success": True,
            "data": {
                "has_portal_access": user_exists,
                "email": client.email,
                "name": client.name,
            }
        })

    if not client.email:
        return Response(
            {"success": False, "message": "Client does not have an email address. Please add an email first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    requested_password = request.data.get("password", "").strip()
    if not requested_password:
        requested_password = generate_temp_password()

    _, final_password = sync_client_portal_user(client, raw_password=requested_password, auto_generate=True)

    return Response({
        "success": True,
        "message": "Client portal credentials generated successfully.",
        "data": {
            "client_id": client.id,
            "client_name": client.name,
            "email": client.email,
            "password": final_password,
            "login_url": "/login",
        }
    })
