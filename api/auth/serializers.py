from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from api.models import BusinessProfile, AppSettings

User = get_user_model()


DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com",
    "tempmail.com",
    "temp-mail.org",
    "10minutemail.com",
    "guerrillamail.com",
    "trashmail.com",
    "trashmail.net",
    "yopmail.com",
    "yopmail.fr",
    "throwawaymail.com",
    "sharklasers.com",
    "getairmail.com",
    "dispostable.com",
    "fakeinbox.com",
    "mohmal.com",
    "tempail.com",
    "burnermail.io",
    "nada.ltd",
}


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
    )

    name = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
        required=False,
        allow_blank=True,
    )

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    role = serializers.CharField(
        default="client",
        required=False,
        allow_blank=True,
    )

    def validate_email(self, value):
        import socket

        value = value.strip().lower()

        # Check existing user
        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "This email is already registered. Please log in instead."
            )

        # Check domain validity
        if "@" in value:
            domain = value.split("@")[-1].strip().lower()

            # 1. Block known disposable/throwaway domains
            if domain in DISPOSABLE_EMAIL_DOMAINS:
                raise serializers.ValidationError(
                    "Temporary or disposable email addresses are not allowed. Please use a valid email."
                )

            # 2. Verify domain format
            if "." not in domain or len(domain.split(".")[-1]) < 2:
                raise serializers.ValidationError(
                    f"The domain '@{domain}' is invalid. Please enter a real email address."
                )

        return value


    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        # Normalize username from name if not given
        if not attrs.get("username"):
            attrs["username"] = (attrs.get("name") or attrs["email"].split("@")[0]).strip()

        # Normalize role
        role_val = str(attrs.get("role") or "client").strip().lower()
        if role_val not in ["super_admin", "admin", "vendor", "client"]:
            role_val = "client"
        attrs["role"] = role_val

        return attrs


    def create(self, validated_data):
        import uuid

        validated_data.pop("password_confirm", None)

        role = validated_data.pop("role", "client")

        username = validated_data["username"].strip()
        email = validated_data["email"].strip().lower()
        password = validated_data["password"]

        # Django username must remain unique.
        unique_username = (
            username
            + "_"
            + uuid.uuid4().hex[:6]
        )

        with transaction.atomic():
            user = User.objects.create_user(
                username=unique_username,
                email=email,
                password=password,
                first_name=username,
                is_staff=(role in ["admin", "super_admin"]),
                is_superuser=(role == "super_admin"),
            )

            if role in ["admin", "super_admin"]:
                business, _ = BusinessProfile.objects.get_or_create(
                    owner=user,
                    defaults={
                        "business_name": f"{username}'s Business",
                        "email": email,
                    },
                )
                AppSettings.objects.get_or_create(
                    business=business,
                )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
    )

    role = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_role(self, value):
        if value:
            v = str(value).strip().lower()
            if v in ["super_admin", "admin", "vendor", "client"]:
                return v
        return None



class UserResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()
    role = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LoginDataSerializer(serializers.Serializer):
    user = UserResponseSerializer()
    tokens = TokenResponseSerializer()


class LoginResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    data = LoginDataSerializer()


class RegisterResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    data = LoginDataSerializer()


class RefreshTokenInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
    )


class RefreshTokenResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    access = serializers.CharField()
    data = serializers.DictField()


class LogoutInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
    )


class MessageResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        min_length=6,
    )

    new_password_confirm = serializers.CharField(
        write_only=True,
        min_length=6,
        required=False,
    )

    def validate(self, attrs):
        confirm = attrs.get("new_password_confirm")
        if confirm and attrs["new_password"] != confirm:
            raise serializers.ValidationError({
                "new_password_confirm": "Passwords do not match."
            })

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({
                "new_password": "New password must be different from old password."
            })

        return attrs



class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    otp = serializers.CharField(required=False, allow_blank=True, max_length=10)
    uid = serializers.CharField(required=False, allow_blank=True)
    token = serializers.CharField(required=False, allow_blank=True)

    password = serializers.CharField(
        min_length=8,
        write_only=True,
    )

    password_confirm = serializers.CharField(
        min_length=8,
        write_only=True,
    )

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        if not (attrs.get("email") and attrs.get("otp")) and not (attrs.get("uid") and attrs.get("token")):
            raise serializers.ValidationError({
                "otp": "Please provide your email and 6-digit verification code."
            })

        return attrs


class GoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Google ID token (credential) obtained from Google Identity Services",
    )
    role = serializers.CharField(
        default="client",
        required=False,
        allow_blank=True,
    )
    mode = serializers.CharField(
        default="login",
        required=False,
        allow_blank=True,
    )

    def validate_role(self, value):
        if value:
            v = str(value).strip().lower()
            if v in ["super_admin", "admin", "vendor", "client"]:
                return v
        return "client"

    def validate_mode(self, value):
        if value:
            v = str(value).strip().lower()
            if v in ["login", "signup", "register"]:
                return "signup" if v in ["signup", "register"] else "login"
        return "login"

