from decimal import Decimal

from rest_framework import serializers

from ..models import Client


from django.contrib.auth import get_user_model

User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    quote_count = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    outstanding = serializers.SerializerMethodField()
    has_portal_access = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )
    create_portal_access = serializers.BooleanField(
        write_only=True,
        required=False,
        default=True,
    )

    class Meta:
        model = Client

        fields = [
            "id",
            "name",
            "company_name",
            "email",
            "phone",
            "address",
            "notes",
            "is_active",
            "quote_count",
            "invoice_count",
            "outstanding",
            "has_portal_access",
            "password",
            "create_portal_access",
        ]

    def get_has_portal_access(self, obj):
        if not obj.email:
            return False
        return User.objects.filter(email__iexact=obj.email).exists()

    def get_quote_count(self, obj):
        return obj.quotes.count()

    def get_invoice_count(self, obj):
        return obj.invoices.count()

    def get_outstanding(self, obj):
        total = Decimal("0.00")

        invoices = obj.invoices.all()

        for invoice in invoices:
            invoice_total = (
                invoice.total
                if invoice.total is not None
                else Decimal("0.00")
            )

            paid_amount = (
                invoice.paid_amount
                if invoice.paid_amount is not None
                else Decimal("0.00")
            )

            total += invoice_total - paid_amount

        return max(total, Decimal("0.00"))