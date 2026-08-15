from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from api.models import BusinessProfile, AppSettings

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        trim_whitespace=True,
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

    role = serializers.ChoiceField(
        choices=["admin", "client"],
        default="client",
        required=False,
    )

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "This email is already registered. Please log in instead."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

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
                is_staff=(role == "admin"),
            )

            business = BusinessProfile.objects.create(
                owner=user,
                business_name=f"{username}'s Business",
                email=email,
            )

            AppSettings.objects.create(
                business=business,
            )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
    )

    role = serializers.ChoiceField(
        choices=["admin", "client"],
        required=False,
        allow_blank=True,
    )


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
        min_length=8,
    )

    new_password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
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
    uid = serializers.CharField()
    token = serializers.CharField()

    password = serializers.CharField(
        min_length=8,
        write_only=True,
    )

    password_confirm = serializers.CharField(
        min_length=8,
        write_only=True,
    )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        return attrs