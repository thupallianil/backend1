import os
import uuid
import random
import logging
import requests
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
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

from api.models import (
    BusinessProfile,
    AppSettings,
    SignupVerificationOTP,
    PasswordResetOTP,
    UserProfile,
    Vendor,
    Client,
)

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    GoogleAuthSerializer,
    RefreshTokenInputSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)

logger = logging.getLogger(__name__)

import secrets


def generate_secure_otp():
    """Generates a cryptographically secure 6-digit OTP string."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def send_otp_email(email, otp, name="User", purpose="signup"):
    """
    Dispatches a branded, secure HTML & text OTP email.
    """
    is_reset = (purpose == "reset")
    if is_reset:
        subject = f"{otp} is your password recovery code"
        title = "Reset Your Password"
        desc = "You recently requested to reset your password. Use the verification code below to proceed."
        expiry_note = "This password recovery code expires in 5 minutes."
        action_note = "If you did not request a password reset, please ignore this email. Your account remains secure."
    else:
        subject = f"{otp} is your verification code"
        title = "Verify Your Email Address"
        desc = "Thank you for joining InvoiceFlow. Use the 6-digit verification code below to activate your account."
        expiry_note = "This verification code expires in 5 minutes."
        action_note = "If you did not request this registration, you can safely ignore this email."

    plain_message = (
        f"Hello {name},\n\n"
        f"Your verification code is: {otp}\n\n"
        f"{expiry_note}\n\n"
        f"{action_note}\n\n"
        f"Regards,\nInvoiceFlow Team"
    )

    html_message = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px 24px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; color: #1e293b;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; width: 44px; height: 44px; background: #2563eb; border-radius: 12px; line-height: 44px; color: #ffffff; font-size: 22px; font-weight: bold; margin-bottom: 12px;">IF</div>
            <h2 style="color: #0f172a; margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">{title}</h2>
            <p style="color: #64748b; font-size: 14px; margin-top: 6px; line-height: 1.5;">{desc}</p>
        </div>
        <div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 14px; padding: 24px; text-align: center; margin: 24px 0;">
            <span style="font-family: monospace; font-size: 38px; font-weight: 900; letter-spacing: 8px; color: #2563eb; display: block;">{otp}</span>
            <p style="color: #64748b; font-size: 12px; font-weight: 600; margin-top: 10px; margin-bottom: 0;">{expiry_note}</p>
        </div>
        <p style="color: #64748b; font-size: 12px; line-height: 1.6; margin-bottom: 24px;">{action_note}</p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">&copy; {timezone.now().year} InvoiceFlow Enterprise. All rights reserved.</p>
    </div>
    """

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@invoiceflow.com"
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"OTP email ({purpose}) sent to {email}")
    except Exception as e:
        logger.warning(f"SMTP dispatch note for {email}: {e}")

    # Log in console only during local debug development
    if getattr(settings, "DEBUG", False):
        print(f"\n=======================================================\n[DEBUG OTP - {purpose.upper()}] Sent to: {email} | CODE: {otp}\n=======================================================\n")


User = get_user_model()


def get_user_role(user):
    if not user or not getattr(user, "is_authenticated", True):
        return "client"

    # 1. Super Admin: superuser flag
    if getattr(user, "is_superuser", False):
        return "super_admin"

    # 2. Explicit UserProfile record
    profile = getattr(user, "profile", None)
    if profile and profile.role:
        return profile.role

    # 3. Vendor link or records
    if getattr(user, "vendor_records", None) and user.vendor_records.exists():
        return "vendor"
    if Vendor.objects.filter(email__iexact=user.email).exists():
        return "vendor"

    # 4. Admin: is_staff or BusinessProfile owner
    if getattr(user, "is_staff", False) or BusinessProfile.objects.filter(owner=user).exists():
        return "admin"

    # 5. Client
    return "client"


def user_data(user):
    role = get_user_role(user)
    profile = getattr(user, "profile", None)
    avatar_url = ""
    if profile and profile.avatar:
        try:
            avatar_url = profile.avatar.url
        except Exception:
            avatar_url = str(profile.avatar)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.get_full_name() or user.first_name or user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "role": role,
        "phone": profile.phone if profile else "",
        "avatar": avatar_url,
    }



def token_data(user):
    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# ============================================================
# STEP 1: REQUEST SIGNUP OTP
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def request_signup_otp(request):
    """
    Validates registration details without creating the user account.
    Generates a 6-digit OTP (expires in 5 minutes) and dispatches it via email.
    """
    try:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            first_err = "Validation failed."
            for field, err_list in serializer.errors.items():
                if isinstance(err_list, list) and len(err_list) > 0:
                    first_err = f"{err_list[0]}"
                    break
                elif isinstance(err_list, str):
                    first_err = err_list
                    break
            return Response(
                {
                    "success": False,
                    "message": first_err,
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = serializer.validated_data
        email = validated["email"].strip().lower()
        username = validated.get("username", email.split("@")[0]).strip()
        password = validated["password"]
        role = validated.get("role", "client")

        # Check if email is already registered and verified
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {
                    "success": False,
                    "message": "An account with this email address already exists. Please log in instead.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resend cooldown: Check if an active OTP was created in the last 60 seconds
        recent_otp = SignupVerificationOTP.objects.filter(email__iexact=email).order_by("-created_at").first()
        if recent_otp:
            elapsed = (timezone.now() - recent_otp.created_at).total_seconds()
            if elapsed < 60:
                remaining = int(60 - elapsed)
                return Response(
                    {
                        "success": False,
                        "message": f"Please wait {remaining} seconds before requesting a new verification code.",
                        "cooldown": remaining,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        # Generate cryptographically secure 6-digit OTP (5 min expiry)
        otp = generate_secure_otp()
        expires_at = timezone.now() + timedelta(minutes=5)

        # Invalidate previous OTP records for this email
        SignupVerificationOTP.objects.filter(email__iexact=email).delete()

        # Store pending registration in temporary data
        company_name = str(request.data.get("company_name", "")).strip()
        SignupVerificationOTP.objects.create(
            email=email,
            otp=otp,
            temp_data={
                "username": username,
                "email": email,
                "password": password,
                "role": role,
                "company_name": company_name or f"{username}'s Business",
            },
            expires_at=expires_at,
            attempts=0,
        )

        # Dispatch verification email
        send_otp_email(email, otp, username, purpose="signup")

        is_console_backend = getattr(settings, "EMAIL_BACKEND", "").endswith("console.EmailBackend") or getattr(settings, "DEBUG", False)
        debug_otp = otp if is_console_backend else None

        return Response(
            {
                "success": True,
                "message": f"Verification code sent to {email}." if not debug_otp else f"Verification code sent! (Testing code: {otp})",
                "otp": debug_otp,
                "data": {
                    "email": email,
                    "otp": debug_otp,
                },
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.exception("Unexpected error in request_signup_otp")
        return Response(
            {
                "success": False,
                "message": f"Registration request failed: {str(e)}",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )



# ============================================================
# STEP 2: VERIFY SIGNUP OTP & CREATE ACCOUNT
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def verify_signup_otp(request):
    """
    Verifies the 6-digit OTP. If correct, creates the user account and profile atomically.
    """
    email = str(request.data.get("email", "")).strip().lower()
    otp = str(request.data.get("otp", "")).strip()

    if not email or not otp:
        return Response(
            {
                "success": False,
                "message": "Both email and 6-digit verification code are required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp_record = SignupVerificationOTP.objects.filter(email__iexact=email).order_by("-created_at").first()

    if not otp_record:
        return Response(
            {
                "success": False,
                "message": "No pending registration found for this email. Please request a new code.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check maximum attempt limit (5 attempts max)
    if otp_record.attempts >= 5:
        otp_record.delete()
        return Response(
            {
                "success": False,
                "message": "Too many attempts. Please request a new verification code.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check expiration (5 minutes)
    if timezone.now() > otp_record.expires_at:
        otp_record.delete()
        return Response(
            {
                "success": False,
                "message": "This verification code has expired. Please request a new code.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(otp_record.otp.strip(), otp):
        otp_record.attempts += 1
        otp_record.save(update_fields=["attempts"])
        if otp_record.attempts >= 5:
            otp_record.delete()
            return Response(
                {
                    "success": False,
                    "message": "Too many attempts. Please request a new verification code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "success": False,
                "message": "Invalid verification code. Please try again.",
                "attempts_remaining": 5 - otp_record.attempts,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Double check email uniqueness before committing
    if User.objects.filter(email__iexact=email).exists():
        otp_record.delete()
        return Response(
            {
                "success": False,
                "message": "An account with this email address already exists. Please log in instead.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Valid OTP -> Atomically provision User and associated profile
    temp_data = otp_record.temp_data or {}
    username = temp_data.get("username", email.split("@")[0]).strip()
    password = temp_data.get("password")
    role = temp_data.get("role", "client")
    company_name = temp_data.get("company_name") or f"{username}'s Business"

    unique_username = f"{username}_{uuid.uuid4().hex[:6]}"

    with transaction.atomic():
        user = User.objects.create_user(
            username=unique_username,
            email=email,
            password=password,
            first_name=username,
            is_staff=(role in ["admin", "super_admin"]),
            is_superuser=(role == "super_admin"),
        )

        UserProfile.objects.get_or_create(
            user=user,
            defaults={"role": role},
        )

        if role == "admin":
            business, _ = BusinessProfile.objects.get_or_create(
                owner=user,
                defaults={
                    "business_name": company_name or f"{username}'s Business",
                    "email": user.email,
                },
            )
            AppSettings.objects.get_or_create(business=business)
        elif role == "vendor":
            default_biz = BusinessProfile.objects.first()
            if default_biz:
                Vendor.objects.get_or_create(
                    email=user.email,
                    defaults={
                        "name": username,
                        "company_name": company_name or f"{username} Supplies",
                        "business": default_biz,
                        "user": user,
                    },
                )
        elif role == "client":
            default_biz = BusinessProfile.objects.first()
            if default_biz:
                from api.models import Client
                Client.objects.get_or_create(
                    email=user.email,
                    defaults={
                        "name": username,
                        "company_name": company_name or f"{username} Enterprises",
                        "business": default_biz,
                        "user": user,
                    },
                )

        # Single-use: delete OTP record after successful account creation
        otp_record.delete()

    tokens = token_data(user)

    return Response(
        {
            "success": True,
            "message": "Email verified successfully. Account created.",
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "data": {
                "user": user_data(user),
                "tokens": tokens,
                "access": tokens["access"],
                "refresh": tokens["refresh"],
            },
        },
        status=status.HTTP_201_CREATED,
    )


# ============================================================
# RESEND SIGNUP OTP
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def resend_signup_otp(request):
    """
    Resends a new 6-digit verification code with a 60-second cooldown.
    """
    email = str(request.data.get("email", "")).strip().lower()

    if not email:
        return Response(
            {
                "success": False,
                "message": "Email is required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp_record = SignupVerificationOTP.objects.filter(email__iexact=email).order_by("-created_at").first()

    if not otp_record:
        return Response(
            {
                "success": False,
                "message": "No pending registration found for this email. Please sign up again.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 60s cooldown check
    elapsed = (timezone.now() - otp_record.created_at).total_seconds()
    if elapsed < 60:
        remaining = int(60 - elapsed)
        return Response(
            {
                "success": False,
                "message": f"Please wait {remaining} seconds before requesting a new verification code.",
                "cooldown": remaining,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Generate fresh OTP and reset expiry to 5 mins
    new_otp = generate_secure_otp()
    otp_record.otp = new_otp
    otp_record.expires_at = timezone.now() + timedelta(minutes=5)
    otp_record.attempts = 0
    otp_record.save()

    username = otp_record.temp_data.get("username", "User")
    send_otp_email(email, new_otp, username, purpose="signup")

    is_console_backend = getattr(settings, "EMAIL_BACKEND", "").endswith("console.EmailBackend") or getattr(settings, "DEBUG", False)
    debug_otp = new_otp if is_console_backend else None

    return Response(
        {
            "success": True,
            "message": "A new verification code has been sent." if not debug_otp else f"New verification code sent! (Testing code: {new_otp})",
            "otp": debug_otp,
            "data": {
                "email": email,
                "otp": debug_otp,
            },
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# LEGACY / DIRECT REGISTER (Fallback)
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

    # Super Admin can authenticate through any portal tab
    if authenticated_user.is_superuser or actual_role == "super_admin":
        pass
    elif requested_role and requested_role != actual_role:
        # Check if staff/admin
        if requested_role in ["admin", "super_admin"] and (authenticated_user.is_staff or actual_role in ["admin", "super_admin"]):
            pass
        else:
            role_map = {
                "super_admin": "Super Admin",
                "admin": "Admin",
                "vendor": "Vendor",
                "client": "Client",
            }
            target_portal = role_map.get(actual_role, actual_role.title())
            current_portal = role_map.get(requested_role, requested_role.title())
            return Response(
                {
                    "success": False,
                    "message": f"This account is registered as a {target_portal}. Please switch to the {target_portal} login tab.",
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
            "access": tokens["access"],
            "refresh": tokens["refresh"],
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
        if "last_name" in data:
            user.last_name = str(data.get("last_name") or "").strip()
        if "email" in data:
            email_val = str(data.get("email") or "").strip().lower()
            if email_val:
                if User.objects.filter(email__iexact=email_val).exclude(pk=user.pk).exists():
                    return Response(
                        {
                            "success": False,
                            "message": "This email address is already in use by another account.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                user.email = email_val
        user.save()

        # Update UserProfile (phone & avatar)
        from api.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if "phone" in data:
            profile.phone = str(data.get("phone") or "").strip()
            profile.save()

        if "avatar" in request.FILES:
            profile.avatar = request.FILES["avatar"]
            profile.save()
        elif "avatar" in data and str(data["avatar"]).startswith("data:image"):
            import base64
            from django.core.files.base import ContentFile
            try:
                format, imgstr = str(data["avatar"]).split(";base64,")
                ext = format.split("/")[-1]
                profile.avatar.save(f"avatar_{user.id}.{ext}", ContentFile(base64.b64decode(imgstr)), save=True)
            except Exception as e:
                logger.warning(f"Failed to parse base64 avatar: {e}")

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
@permission_classes([AllowAny])
def logout(request):
    try:
        data = request.data or {}
        refresh_token = data.get("refresh") or data.get("refresh_token")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
    except Exception:
        pass

    return Response({
        "success": True,
        "message": "Logged out successfully.",
    }, status=status.HTTP_200_OK)


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
    old_password = serializer.validated_data["old_password"]
    new_password = serializer.validated_data["new_password"]

    if not user.check_password(old_password):
        return Response(
            {
                "success": False,
                "message": "Current password is incorrect.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=["password"])

    return Response({
        "success": True,
        "message": "Password changed successfully.",
    })



# ============================================================
# FORGOT PASSWORD (OTP GENERATION & DISPATCH)
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"].strip().lower()

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        return Response(
            {
                "success": False,
                "message": "No account found with this email address. Please check your email or sign up.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 60s cooldown check
    recent_reset = PasswordResetOTP.objects.filter(email__iexact=email).order_by("-created_at").first()
    if recent_reset:
        elapsed = (timezone.now() - recent_reset.created_at).total_seconds()
        if elapsed < 60:
            remaining = int(60 - elapsed)
            return Response(
                {
                    "success": False,
                    "message": f"Please wait {remaining} seconds before requesting a new verification code.",
                    "cooldown": remaining,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

    # Generate 6-digit OTP (5 min expiry)
    otp = generate_secure_otp()
    expires_at = timezone.now() + timedelta(minutes=5)

    # Invalidate older reset OTP records
    PasswordResetOTP.objects.filter(email__iexact=email).delete()

    PasswordResetOTP.objects.create(
        email=email,
        otp=otp,
        expires_at=expires_at,
        attempts=0,
    )

    # Send password reset email
    send_otp_email(email, otp, user.get_full_name() or user.username, purpose="reset")

    is_console_backend = getattr(settings, "EMAIL_BACKEND", "").endswith("console.EmailBackend") or getattr(settings, "DEBUG", False)
    debug_otp = otp if is_console_backend else None

    return Response({
        "success": True,
        "message": f"Password reset verification code sent to {email}." if not debug_otp else f"Password reset code: {otp}",
        "otp": debug_otp,
        "data": {
            "email": email,
            "otp": debug_otp,
        },
    })


# ============================================================
# RESEND PASSWORD RESET OTP
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def resend_password_reset_otp(request):
    email = str(request.data.get("email", "")).strip().lower()

    if not email:
        return Response(
            {
                "success": False,
                "message": "Email is required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return Response(
            {
                "success": False,
                "message": "No account found with this email address.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp_record = PasswordResetOTP.objects.filter(email__iexact=email).order_by("-created_at").first()

    if not otp_record:
        return Response(
            {
                "success": False,
                "message": "No active password reset request found. Please request a new code.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 60s cooldown check
    elapsed = (timezone.now() - otp_record.created_at).total_seconds()
    if elapsed < 60:
        remaining = int(60 - elapsed)
        return Response(
            {
                "success": False,
                "message": f"Please wait {remaining} seconds before requesting a new verification code.",
                "cooldown": remaining,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Generate fresh OTP (5 min expiry)
    new_otp = generate_secure_otp()
    otp_record.otp = new_otp
    otp_record.expires_at = timezone.now() + timedelta(minutes=5)
    otp_record.attempts = 0
    otp_record.save()

    send_otp_email(email, new_otp, user.get_full_name() or user.username, purpose="reset")

    is_console_backend = getattr(settings, "EMAIL_BACKEND", "").endswith("console.EmailBackend") or getattr(settings, "DEBUG", False)
    debug_otp = new_otp if is_console_backend else None

    return Response({
        "success": True,
        "message": "A new verification code has been sent." if not debug_otp else f"New password reset code: {new_otp}",
        "otp": debug_otp,
        "data": {
            "email": email,
            "otp": debug_otp,
        },
    })


# ============================================================
# RESET PASSWORD (OTP OR LINK TOKEN)
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    data = request.data or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    uid = data.get("uid")
    token = data.get("token")
    password = data.get("password") or data.get("new_password")
    password_confirm = data.get("password_confirm") or data.get("new_password_confirm") or data.get("confirm_password") or data.get("confirmPassword")

    if not password:
        return Response(
            {
                "success": False,
                "message": "New password is required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {
                "success": False,
                "message": "Password must be at least 8 characters.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password_confirm and password != password_confirm:
        return Response(
            {
                "success": False,
                "message": "Passwords do not match.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. OTP-Based Verification Flow
    if otp and email:
        otp_record = PasswordResetOTP.objects.filter(email__iexact=email).order_by("-created_at").first()

        if not otp_record:
            return Response(
                {
                    "success": False,
                    "message": "No active password reset request found. Please request a new code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_record.attempts >= 5:
            otp_record.delete()
            return Response(
                {
                    "success": False,
                    "message": "Too many attempts. Please request a new verification code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > otp_record.expires_at:
            otp_record.delete()
            return Response(
                {
                    "success": False,
                    "message": "This verification code has expired. Please request a new code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Constant-time comparison
        if not secrets.compare_digest(otp_record.otp.strip(), otp):
            otp_record.attempts += 1
            otp_record.save(update_fields=["attempts"])
            if otp_record.attempts >= 5:
                otp_record.delete()
                return Response(
                    {
                        "success": False,
                        "message": "Too many attempts. Please request a new verification code.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "success": False,
                    "message": "Invalid verification code. Please try again.",
                    "attempts_remaining": 5 - otp_record.attempts,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            otp_record.delete()
            return Response(
                {
                    "success": False,
                    "message": "User account not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            user.set_password(password)
            user.save(update_fields=["password"])
            # Invalidate all reset OTPs for this email
            PasswordResetOTP.objects.filter(email__iexact=email).delete()

        return Response({
            "success": True,
            "message": "Password reset successfully! You can now log in with your new password.",
        })

    # 2. Token-Based Verification Flow (from backup reset link)
    if uid and token:
        try:
            uid_value = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=uid_value)
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Invalid password reset request link.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {
                    "success": False,
                    "message": "Invalid or expired password reset token.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(password)
            user.save(update_fields=["password"])
            PasswordResetOTP.objects.filter(email__iexact=user.email).delete()

        return Response({
            "success": True,
            "message": "Password reset successfully! You can now log in with your new password.",
        })

    return Response(
        {
            "success": False,
            "message": "Invalid request. Please provide the 6-digit verification code.",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )



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
    mode = serializer.validated_data.get("mode", "login")
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

    # Look up existing user
    user = User.objects.filter(email__iexact=email).first()

    # ============================================================
    # MODE 1: LOGIN (Only existing users allowed)
    # ============================================================
    if mode == "login":
        if not user:
            return Response(
                {
                    "success": False,
                    "message": "No registered account found with this Google email. Please sign up to create your account first.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "message": "This account is inactive. Please contact support.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        actual_role = get_user_role(user)
        if role:
            role_map = {
                "super_admin": "Super Admin",
                "admin": "Admin",
                "vendor": "Vendor",
                "client": "Client",
            }
            matched = (role == actual_role) or (role == "admin" and actual_role == "super_admin")
            if not matched:
                target_portal = role_map.get(actual_role, actual_role.title())
                current_portal = role_map.get(role, role.title())
                return Response(
                    {
                        "success": False,
                        "message": f"This Google account is registered as a {target_portal}. You cannot login through the {current_portal} portal. Please switch to the {target_portal} login tab.",
                        "role": actual_role,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Update profile names if previously blank
        updated_fields = []
        if not user.first_name and (given_name or display_name):
            user.first_name = given_name or display_name
            updated_fields.append("first_name")
        if not user.last_name and family_name:
            user.last_name = family_name
            updated_fields.append("last_name")
        if updated_fields:
            user.save(update_fields=updated_fields)

        tokens = token_data(user)
        return Response(
            {
                "success": True,
                "message": f"Welcome back, {user.first_name or user.username}!",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "data": {
                    "user": user_data(user),
                    "tokens": tokens,
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                },
            },
            status=status.HTTP_200_OK,
        )

    # ============================================================
    # MODE 2: SIGNUP / REGISTER (Create new user and initialize profile)
    # ============================================================
    else:
        if user:
            return Response(
                {
                    "success": False,
                    "message": "An account with this Google email already exists. Please sign in instead.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        unique_username = f"google_{email.split('@')[0]}_{uuid.uuid4().hex[:6]}"

        with transaction.atomic():
            user = User.objects.create_user(
                username=unique_username,
                email=email,
                first_name=given_name or display_name,
                last_name=family_name,
                is_staff=(role in ["admin", "super_admin"]),
                is_superuser=(role == "super_admin"),
            )
            user.set_unusable_password()
            user.save()

            UserProfile.objects.get_or_create(
                user=user,
                defaults={"role": role or "client"},
            )

            if role == "admin":
                business, _ = BusinessProfile.objects.get_or_create(
                    owner=user,
                    defaults={
                        "business_name": f"{display_name}'s Business",
                        "email": email,
                    },
                )
                AppSettings.objects.get_or_create(business=business)
            elif role == "vendor":
                default_biz = BusinessProfile.objects.first()
                if default_biz:
                    Vendor.objects.get_or_create(
                        email=email,
                        defaults={
                            "name": display_name or given_name or "Vendor",
                            "company_name": f"{display_name}'s Supplies",
                            "business": default_biz,
                            "user": user,
                        },
                    )

        tokens = token_data(user)
        return Response(
            {
                "success": True,
                "message": f"Account created successfully! Welcome, {user.first_name}!",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "data": {
                    "user": user_data(user),
                    "tokens": tokens,
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                },
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# SEED PRODUCTION DATABASE ENDPOINT (One-Click Auto-Provisioning)
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def seed_database_endpoint(request):
    """
    Initializes and seeds the production database with all core multi-tenant roles,
    businesses, and user accounts. Can be triggered on Render/Railway after deployment.
    """
    try:
        from seed_full_multitenant_data import seed
        seed()
        return Response(
            {
                "success": True,
                "message": "Production multi-tenant database seeded and verified successfully!",
                "accounts": [
                    {"role": "Super Admin", "email": "thupallianil12@gmail.com", "pass": "SuperAdmin@123"},
                    {"role": "Super Admin (Global)", "email": "admin@invoiceflow.com", "pass": "Admin@123"},
                    {"role": "Admin", "email": "thupallianil012345@gmail.com", "pass": "Admin@123"},
                    {"role": "Vendor", "email": "thupallianil@gmail.com", "pass": "Admin@123"},
                    {"role": "Client", "email": "thupallianil108@gmail.com", "pass": "Admin@123"},
                ]
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": f"Database seeding failed: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

