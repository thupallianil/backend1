from rest_framework import serializers
from api.models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True,
    )
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "company_name",
            "display_name",
            "email",
            "phone",
            "category",
            "category_display",
            "tax_number",
            "pan_number",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "website",
            "bank_name",
            "account_name",
            "account_number",
            "ifsc_code",
            "upi_id",
            "payment_terms",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_display_name(self, obj):
        if obj.company_name and obj.name:
            return f"{obj.company_name} ({obj.name})"
        return obj.company_name or obj.name or f"Vendor #{obj.id}"
