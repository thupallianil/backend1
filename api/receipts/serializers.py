from rest_framework import serializers

from api.models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(
        source="invoice.invoice_number",
        read_only=True,
    )

    client_name = serializers.CharField(
        source="invoice.client.name",
        read_only=True,
        default="",
    )

    client_email = serializers.CharField(
        source="invoice.client.email",
        read_only=True,
        default="",
    )

    payment_method = serializers.CharField(
        source="payment.method",
        read_only=True,
        default="",
    )

    gateway_payment_id = serializers.CharField(
        source="payment.gateway_payment_id",
        read_only=True,
        default="",
    )

    transaction_id = serializers.CharField(
        source="payment.transaction_id",
        read_only=True,
        default="",
    )

    business_name = serializers.CharField(
        source="business.business_name",
        read_only=True,
        default="",
    )

    invoice_id = serializers.IntegerField(
        source="invoice.id",
        read_only=True,
    )

    class Meta:
        model = Receipt

        fields = [
            "id",
            "payment",
            "invoice",
            "invoice_id",
            "invoice_number",
            "client_name",
            "client_email",
            "payment_method",
            "transaction_id",
            "gateway_payment_id",
            "business_name",
            "receipt_number",
            "amount",
            "issued_date",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "invoice_id",
            "invoice_number",
            "client_name",
            "client_email",
            "payment_method",
            "transaction_id",
            "gateway_payment_id",
            "business_name",
            "created_at",
            "updated_at",
        ]