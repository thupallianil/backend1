from rest_framework import serializers

from api.models import Payment


class PaymentSerializer(
    serializers.ModelSerializer
):

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )
        return value

    invoice_number = serializers.CharField(
        source="invoice.invoice_number",
        read_only=True,
    )

    client_name = serializers.CharField(
        source="invoice.client.name",
        read_only=True,
    )

    receipt_id = serializers.IntegerField(
        source="receipt.id",
        read_only=True,
        default=None,
    )

    receipt_number = serializers.CharField(
        source="receipt.receipt_number",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Payment

        fields = [
            "id",
            "invoice",
            "invoice_number",
            "client_name",
            "amount",
            "method",
            "status",
            "transaction_id",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway_signature",
            "paid_at",
            "receipt_id",
            "receipt_number",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "invoice_number",
            "client_name",
            "status",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway_signature",
            "paid_at",
            "receipt_id",
            "receipt_number",
            "created_at",
            "updated_at",
        ]
