import os
import uuid
import logging
import requests

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

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

from api.models import BusinessProfile, AppSettings

logger = logging.getLogger(__name__)



from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    GoogleAuthSerializer,
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
            target_portal = "Admin" if actual_role == "admin" else "Client"
            current_portal = "Admin" if requested_role == "admin" else "Client"
            return Response(
                {
                    "success": False,
                    "message": f"This account is registered as a {target_portal}. You cannot login through the {current_portal} portal. Please switch to the {target_portal} login tab.",
                    "role": actual_role,
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

    reset_url = None
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        frontend_url = os.environ.get("FRONTEND_URL", "https://frontend-gray-nu-88.vercel.app").rstrip("/")
        reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

        try:
            from django.core.mail import send_mail
            subject = "Password Reset Instructions"
            message = (
                f"Hello {user.get_full_name() or user.username},\n\n"
                f"You recently requested to reset your password.\n"
                f"Please click the link below to set a new password:\n\n"
                f"{reset_url}\n\n"
                f"If you did not make this request, you can safely ignore this email.\n\n"
                f"Regards,\nSupport Team"
            )
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ultrakeyit.com")
            send_mail(subject, message, from_email, [email], fail_silently=True)
        except Exception as e:
            logger.warning("Failed to send password reset email: %s", str(e))

    return Response({
        "success": True,
        "message": "If the email exists in our system, password reset instructions have been sent.",
        "data": {
            "email": email,
            "user_found": bool(user),
            "reset_url": reset_url if getattr(settings, "DEBUG", False) else None,
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


# ============================================================
# GOOGLE OAUTH
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def google_auth(request):
    """
    Verifies Google ID token from frontend, finds or provisions the User,
    and returns application SimpleJWT access & refresh tokens.
    """
    serializer = GoogleAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    token = serializer.validated_data["credential"]
    role = serializer.validated_data.get("role", "client")
    google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", "").strip()

    try:
        # Verify token with Google's tokeninfo endpoint
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=10,
        )
        if resp.status_code != 200:
            err_data = {}
            try:
                err_data = resp.json()
            except Exception:
                pass
            err_msg = err_data.get("error_description") or err_data.get("error") or "Invalid Google token."
            return Response(
                {
                    "success": False,
                    "message": f"Google token verification failed: {err_msg}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        id_info = resp.json()

        # If GOOGLE_CLIENT_ID is configured in settings, verify audience matches
        if google_client_id and id_info.get("aud") != google_client_id:
            return Response(
                {
                    "success": False,
                    "message": "Google token was not issued for this application client ID.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as exc:
        return Response(
            {
                "success": False,
                "message": f"Google token verification error: {str(exc)}",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


    email = id_info.get("email", "").strip().lower()
    if not email:
        return Response(
            {
                "success": False,
                "message": "Google account does not contain a verified email address.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    full_name = (id_info.get("name") or "").strip()
    given_name = (id_info.get("given_name") or "").strip()
    family_name = (id_info.get("family_name") or "").strip()

    display_name = full_name or given_name or email.split("@")[0]

    # Find or provision user
    user = User.objects.filter(email__iexact=email).first()

    if user:
        actual_role = get_user_role(user)
        if role and role != actual_role:
            target_portal = "Admin" if actual_role == "admin" else "Client"
            current_portal = "Admin" if role == "admin" else "Client"
            return Response(
                {
                    "success": False,
                    "message": f"This Google account is registered as a {target_portal}. You cannot login through the {current_portal} portal. Please switch to the {target_portal} login tab.",
                    "role": actual_role,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        unique_username = f"google_{email.split('@')[0]}_{uuid.uuid4().hex[:6]}"

        with transaction.atomic():
            user = User.objects.create_user(
                username=unique_username,
                email=email,
                first_name=given_name or display_name,
                last_name=family_name,
                is_staff=(role == "admin"),
            )
            user.set_unusable_password()
            user.save()

            business, _ = BusinessProfile.objects.get_or_create(
                owner=user,
                defaults={
                    "business_name": f"{display_name}'s Business",
                    "email": email,
                },
            )
            AppSettings.objects.get_or_create(business=business)

    tokens = token_data(user)


    return Response(
        {
            "success": True,
            "message": "Google authentication successful.",
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "data": {
                "user": user_data(user),
                "tokens": tokens,
            },
        },
        status=status.HTTP_200_OK,
    )