from rest_framework import serializers
from api.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)
    actor_username = serializers.CharField(source="actor.username", read_only=True)
    business_name = serializers.CharField(source="business.business_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "business",
            "business_name",
            "actor",
            "actor_name",
            "actor_username",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "details",
            "ip_address",
            "created_at",
        ]
