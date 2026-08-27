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

from api.models import BusinessProfile, AppSettings, SignupVerificationOTP, PasswordResetOTP


logger = logging.getLogger(__name__)


def send_otp_email(email, otp, name="User"):
    subject = f"{otp} is your verification code"
    plain_message = (
        f"Hello {name},\n\n"
        f"Your verification code to complete your registration is:\n\n"
        f"{otp}\n\n"
        f"This code is valid for 10 minutes. If you did not request this, please ignore this email.\n"
    )
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #0f172a; margin: 0; font-size: 22px; font-weight: 800;">Verify Your Email Address</h2>
            <p style="color: #64748b; font-size: 13px; margin-top: 6px;">Thank you for registering. Please use the 6-digit verification code below to activate your account.</p>
        </div>
        <div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-family: monospace; font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #2563eb;">{otp}</span>
            <p style="color: #94a3b8; font-size: 11px; margin-top: 8px; margin-bottom: 0;">Code expires in 10 minutes</p>
        </div>
        <p style="color: #64748b; font-size: 12px; line-height: 1.5;">If you did not request this registration, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">&copy; InvoiceFlow Cloud Enterprise. All rights reserved.</p>
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
        logger.info(f"Verification OTP email dispatched to {email}")
    except Exception as e:
        logger.warning(f"SMTP dispatch note for {email}: {e}")
    
    # Always log OTP in console so development & local testing are seamless
    print(f"\n=======================================================\n[EMAIL VERIFICATION OTP] Sent to: {email} | CODE: {otp}\n=======================================================\n")


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
# STEP 1: REQUEST SIGNUP OTP
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def request_signup_otp(request):
    """
    Validates registration details without creating the user account.
    Generates a 6-digit OTP and sends it to the user's email.
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

        # Generate 6-digit OTP
        otp = f"{random.randint(100000, 999999):06d}"
        expires_at = timezone.now() + timedelta(minutes=10)

        # Clear any old OTP records for this email
        SignupVerificationOTP.objects.filter(email__iexact=email).delete()

        # Store pending signup data temporarily
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

        # Send verification email safely
        try:
            send_otp_email(email, otp, username)
        except Exception as mail_err:
            logger.error(f"Error calling send_otp_email: {mail_err}")

        return Response(
            {
                "success": True,
                "message": f"Verification code sent to {email}.",
                "email": email,
                "data": {
                    "email": email,
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
    Verifies the 6-digit OTP. If and only if correct, creates the user account in the database.
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
                "message": "No pending registration found for this email. Please submit the sign-up form again.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check expiration
    if timezone.now() > otp_record.expires_at:
        return Response(
            {
                "success": False,
                "message": "Verification code has expired. Please request a new code.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check attempts
    if otp_record.attempts >= 5:
        return Response(
            {
                "success": False,
                "message": "Too many failed attempts. Please request a new verification code.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate OTP code
    if otp_record.otp.strip() != otp:
        otp_record.attempts += 1
        otp_record.save()
        remaining = 5 - otp_record.attempts
        return Response(
            {
                "success": False,
                "message": f"Invalid verification code. ({remaining} attempts remaining)",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Valid OTP verified -> Create User and BusinessProfile atomically
    temp_data = otp_record.temp_data or {}
    username = temp_data.get("username", email.split("@")[0]).strip()
    password = temp_data.get("password")
    role = temp_data.get("role", "client")
    company_name = temp_data.get("company_name") or f"{username}'s Business"

    # Generate unique username
    unique_username = f"{username}_{uuid.uuid4().hex[:6]}"

    with transaction.atomic():
        user = User.objects.create_user(
            username=unique_username,
            email=email,
            password=password,
            first_name=username,
            is_staff=(role == "admin"),
            is_superuser=(role == "admin"),
        )

        business, _ = BusinessProfile.objects.get_or_create(
            owner=user,
            defaults={
                "business_name": company_name,
                "email": user.email,
            },
        )


        AppSettings.objects.get_or_create(
            business=business,
        )

        # Cleanup OTP record
        otp_record.delete()

    tokens = token_data(user)

    return Response(
        {
            "success": True,
            "message": "Email verified successfully! Account created.",
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
    Resends a new 6-digit verification code to the email.
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

    # Generate fresh OTP
    new_otp = f"{random.randint(100000, 999999):06d}"
    otp_record.otp = new_otp
    otp_record.expires_at = timezone.now() + timedelta(minutes=10)
    otp_record.attempts = 0
    otp_record.save()

    username = otp_record.temp_data.get("username", "User")
    send_otp_email(email, new_otp, username)

    return Response(
        {
            "success": True,
            "message": f"New verification code sent to {email}.",
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

    if not serializer.is_valid():
        first_err = "Invalid password data provided."
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

    user = request.user

    if not user.check_password(
        serializer.validated_data["old_password"]
    ):
        return Response(
            {
                "success": False,
                "message": "Current password is incorrect. Please enter your existing password.",
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
# FORGOT PASSWORD (OTP & LINK GENERATION)
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

    if not user:
        return Response(
            {
                "success": False,
                "message": "No account found with this email address. Please check your email or sign up.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Generate 6-digit OTP code
    otp = f"{random.randint(100000, 999999):06d}"
    expires_at = timezone.now() + timedelta(minutes=10)

    # Clear old reset OTPs
    PasswordResetOTP.objects.filter(email__iexact=email).delete()

    PasswordResetOTP.objects.create(
        email=email,
        otp=otp,
        expires_at=expires_at,
        attempts=0,
    )

    # 2. Generate backup reset link
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

    # 3. Send styled email
    subject = f"{otp} is your password reset code"
    plain_message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"You recently requested to reset your password.\n\n"
        f"Your 6-digit verification code is:\n\n"
        f"{otp}\n\n"
        f"This code will expire in 10 minutes.\n\n"
        f"Alternatively, you can reset your password directly using this link:\n"
        f"{reset_url}\n\n"
        f"If you did not request a password reset, please ignore this email.\n\n"
        f"Regards,\nInvoiceFlow Support Team"
    )

    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #0f172a; margin: 0; font-size: 22px; font-weight: 800;">Password Reset Request</h2>
            <p style="color: #64748b; font-size: 13px; margin-top: 6px;">Use the verification code below to reset your account password.</p>
        </div>
        <div style="background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-family: monospace; font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #2563eb;">{otp}</span>
            <p style="color: #94a3b8; font-size: 11px; margin-top: 8px; margin-bottom: 0;">Code expires in 10 minutes</p>
        </div>
        <p style="color: #64748b; font-size: 12px; line-height: 1.5;">If you did not request a password reset, please ignore this message. Your account remains secure.</p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">&copy; InvoiceFlow Cloud Enterprise. All rights reserved.</p>
    </div>
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@invoiceflow.com"

    try:
        send_mail(subject, plain_message, from_email, [email], html_message=html_message, fail_silently=False)
        logger.info(f"Password reset email sent to {email}")
    except Exception as e:
        logger.warning(f"SMTP note for password reset {email}: {e}")

    # Always log OTP in console so testing is never blocked
    print(f"\n=======================================================\n[PASSWORD RESET OTP] Sent to: {email} | CODE: {otp}\nReset URL: {reset_url}\n=======================================================\n")

    return Response({
        "success": True,
        "message": f"Password reset verification code sent to {email}.",
        "data": {
            "email": email,
            "user_found": True,
            "reset_url": reset_url if getattr(settings, "DEBUG", False) else None,
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


    new_otp = f"{random.randint(100000, 999999):06d}"
    expires_at = timezone.now() + timedelta(minutes=10)

    otp_record, _ = PasswordResetOTP.objects.get_or_create(email=email, defaults={"otp": new_otp, "expires_at": expires_at})
    otp_record.otp = new_otp
    otp_record.expires_at = expires_at
    otp_record.attempts = 0
    otp_record.save()

    subject = f"{new_otp} is your new password reset code"
    plain_message = f"Hello {user.get_full_name() or user.username},\n\nYour new password reset verification code is:\n\n{new_otp}\n\nValid for 10 minutes."
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@invoiceflow.com"

    try:
        send_mail(subject, plain_message, from_email, [email], fail_silently=False)
    except Exception as e:
        logger.warning(f"SMTP note on resend: {e}")

    print(f"\n=======================================================\n[PASSWORD RESET OTP RESENT] Sent to: {email} | CODE: {new_otp}\n=======================================================\n")

    return Response({
        "success": True,
        "message": f"New verification code sent to {email}.",
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
    password = data.get("password")
    password_confirm = data.get("password_confirm")

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

        if timezone.now() > otp_record.expires_at:
            return Response(
                {
                    "success": False,
                    "message": "Verification code has expired. Please request a new code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_record.attempts >= 5:
            return Response(
                {
                    "success": False,
                    "message": "Too many failed attempts. Please request a new code.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_record.otp.strip() != otp:
            otp_record.attempts += 1
            otp_record.save()
            remaining = 5 - otp_record.attempts
            return Response(
                {
                    "success": False,
                    "message": f"Invalid verification code. ({remaining} attempts remaining)",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {
                    "success": False,
                    "message": "User account not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        user.set_password(password)
        user.save(update_fields=["password"])
        otp_record.delete()

        return Response({
            "success": True,
            "message": "Password reset successfully! You can now log in with your new password.",
        })

    # 2. Token-Based Verification Flow (from email link)
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

        user.set_password(password)
        user.save(update_fields=["password"])

        return Response({
            "success": True,
            "message": "Password reset successfully! You can now log in with your new password.",
        })

    return Response(
        {
            "success": False,
            "message": "Please provide the 6-digit verification code or a valid reset token.",
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
                "access": tokens["access"],
                "refresh": tokens["refresh"],
            },
        },
        status=status.HTTP_200_OK,
    )
