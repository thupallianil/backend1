from decimal import Decimal

from rest_framework import serializers

from ..models import Client


class ClientSerializer(serializers.ModelSerializer):
    quote_count = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    outstanding = serializers.SerializerMethodField()

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
        ]

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