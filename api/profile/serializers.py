from rest_framework import serializers

from api.models import BusinessProfile


class ProfileSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(
        source="owner.email",
        read_only=True,
    )

    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = BusinessProfile

        fields = [
            "id",
            "owner_email",
            "business_name",
            "legal_name",
            "email",
            "phone",
            "website",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "tax_number",
            "logo",
            "logo_url",
            "currency",
            "timezone",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "owner_email",
            "logo_url",
            "created_at",
            "updated_at",
        ]

    def get_logo_url(self, obj):
        if not obj.logo:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(
                obj.logo.url
            )

        return obj.logo.url