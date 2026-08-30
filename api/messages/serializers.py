from rest_framework import serializers
from api.models import Message, Project
from django.contrib.auth import get_user_model

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    sender_role = serializers.SerializerMethodField()
    recipient_name = serializers.CharField(source="recipient.get_full_name", read_only=True)
    recipient_username = serializers.CharField(source="recipient.username", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "business",
            "project",
            "project_title",
            "sender",
            "sender_name",
            "sender_username",
            "sender_role",
            "recipient",
            "recipient_name",
            "recipient_username",
            "conversation_type",
            "content",
            "attachment",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "business", "sender", "created_at"]

    def get_sender_role(self, obj):
        profile = getattr(obj.sender, "profile", None)
        if profile:
            return profile.role
        if obj.sender.is_superuser:
            return "super_admin"
        if obj.sender.is_staff:
            return "admin"
        return "client"
