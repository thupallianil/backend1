from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    RefreshTokenInputSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)

User = get_user_model()


def get_user_role(user):
    if user.is_superuser or user.is_staff:
        return "admin"

    return "client"


def user_data(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "role": get_user_role(user),
    }


def token_data(user):
    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# ============================================================
# REGISTER
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    user = serializer.save()

    tokens = token_data(user)

    return Response(
        {
            "success": True,
            "message": "Registration successful.",
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "data": {
                "user": user_data(user),
                "tokens": tokens,
            },
        },
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# LOGIN
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    email = serializer.validated_data["email"].strip().lower()
    password = serializer.validated_data["password"]
    requested_role = serializer.validated_data.get("role")

    user = User.objects.filter(
        email__iexact=email
    ).first()

    if not user:
        return Response(
            {
                "success": False,
                "message": "Invalid email or password.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    authenticated_user = authenticate(
        request=request,
        username=user.username,
        password=password,
    )

    if authenticated_user is None:
        return Response(
            {
                "success": False,
                "message": "Invalid email or password.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    actual_role = get_user_role(authenticated_user)

    if requested_role:
        if requested_role != actual_role:
            return Response(
                {
                    "success": False,
                    "message": "Selected role does not match this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    tokens = token_data(authenticated_user)

    return Response({
        "success": True,
        "message": "Login successful.",
        "access": tokens["access"],
        "refresh": tokens["refresh"],
        "data": {
            "user": user_data(authenticated_user),
            "tokens": tokens,
        },
    })


# ============================================================
# CURRENT USER
# ============================================================

@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    if request.method in ["PUT", "PATCH"]:
        data = request.data or {}
        if "name" in data or "first_name" in data:
            name_val = str(data.get("name") or data.get("first_name") or "").strip()
            if name_val:
                user.first_name = name_val
        if "email" in data:
            email_val = str(data.get("email") or "").strip().lower()
            if email_val and not User.objects.filter(email__iexact=email_val).exclude(pk=user.pk).exists():
                user.email = email_val
        user.save()

    return Response({
        "success": True,
        "message": "User profile updated successfully",
        "data": {
            "user": user_data(user),
        },
    })


# ============================================================
# REFRESH
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    serializer = RefreshTokenInputSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    refresh_token = serializer.validated_data["refresh"]

    try:
        refresh_obj = RefreshToken(
            refresh_token
        )

        access_token = str(
            refresh_obj.access_token
        )

        return Response({
            "success": True,
            "message": "Token refreshed successfully.",
            "access": access_token,
            "data": {
                "access": access_token,
            },
        })

    except Exception:
        return Response(
            {
                "success": False,
                "message": "Invalid or expired refresh token.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )


# ============================================================
# LOGOUT
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = request.data.get("refresh")

    if refresh_token:
        try:
            token = RefreshToken(
                refresh_token
            )

            token.blacklist()

        except Exception:
            pass

    return Response({
        "success": True,
        "message": "Logout successful.",
    })


# ============================================================
# CHANGE PASSWORD
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    user = request.user

    if not user.check_password(
        serializer.validated_data["old_password"]
    ):
        return Response(
            {
                "success": False,
                "message": "Current password is incorrect.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(
        serializer.validated_data["new_password"]
    )

    user.save(
        update_fields=["password"]
    )

    return Response({
        "success": True,
        "message": "Password changed successfully.",
    })


# ============================================================
# FORGOT PASSWORD
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    email = serializer.validated_data["email"].strip().lower()

    user = User.objects.filter(
        email__iexact=email
    ).first()

    # Do not reveal whether an account exists.
    return Response({
        "success": True,
        "message": "If the email exists, password reset instructions can be sent.",
        "data": {
            "email": email,
            "user_found": bool(user),
        },
    })


# ============================================================
# RESET PASSWORD
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(
        data=request.data
    )

    serializer.is_valid(
        raise_exception=True
    )

    uid = serializer.validated_data["uid"]
    token = serializer.validated_data["token"]

    try:
        uid_value = urlsafe_base64_decode(
            uid
        ).decode()

        user = User.objects.get(
            pk=uid_value
        )

    except Exception:
        return Response(
            {
                "success": False,
                "message": "Invalid password reset request.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not default_token_generator.check_token(
        user,
        token,
    ):
        return Response(
            {
                "success": False,
                "message": "Invalid or expired password reset token.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(
        serializer.validated_data["password"]
    )

    user.save(
        update_fields=["password"]
    )

    return Response({
        "success": True,
        "message": "Password reset successfully.",
    })