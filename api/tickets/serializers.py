from rest_framework import serializers
from api.models import Ticket, TicketMessage, Client, BusinessProfile


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = [
            "id",
            "ticket",
            "sender",
            "sender_name",
            "sender_email",
            "sender_role",
            "message",
            "attachment",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "ticket",
            "sender",
            "sender_name",
            "sender_email",
            "sender_role",
            "created_at",
        ]

    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.username or obj.sender.email
        return "Support Team"

    def get_sender_email(self, obj):
        return obj.sender.email if obj.sender else ""


class TicketSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_email = serializers.CharField(source="client.email", read_only=True)
    client_company = serializers.CharField(source="client.company_name", read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)
    messages_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_number",
            "client",
            "client_name",
            "client_email",
            "client_company",
            "created_by",
            "subject",
            "category",
            "priority",
            "status",
            "description",
            "attachment",
            "last_reply_at",
            "messages",
            "messages_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ticket_number",
            "created_by",
            "last_reply_at",
            "created_at",
            "updated_at",
        ]

    def get_messages_count(self, obj):
        return obj.messages.count()
