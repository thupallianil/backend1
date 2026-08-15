from decimal import Decimal

from rest_framework import serializers

from api.models import (
    Invoice,
    InvoiceItem,
)


class InvoiceItemSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = InvoiceItem

        fields = [
            "id",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "discount",
            "amount",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "amount",
            "created_at",
            "updated_at",
        ]


class InvoiceSerializer(
    serializers.ModelSerializer
):

    items = InvoiceItemSerializer(
        many=True,
        required=False,
    )

    # Flat client detail fields — read-only, sourced from related Client model
    client_name = serializers.CharField(
        source="client.name",
        read_only=True,
        allow_null=True,
        default=None,
    )

    client_email = serializers.EmailField(
        source="client.email",
        read_only=True,
        allow_null=True,
        default=None,
    )

    client_phone = serializers.CharField(
        source="client.phone",
        read_only=True,
        allow_null=True,
        default=None,
    )

    client_address = serializers.CharField(
        source="client.address",
        read_only=True,
        allow_null=True,
        default=None,
    )

    client_company = serializers.CharField(
        source="client.company_name",
        read_only=True,
        allow_null=True,
        default=None,
    )

    quote_number = serializers.CharField(
        source="quote.quote_number",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Invoice

        fields = [
            "id",
            "client",
            "client_name",
            "client_email",
            "client_phone",
            "client_address",
            "client_company",
            "quote",
            "quote_number",
            "invoice_number",
            "issue_date",
            "due_date",
            "status",
            "items",
            "subtotal",
            "discount",
            "tax",
            "total",
            "paid_amount",
            "balance_due",
            "notes",
            "terms",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "client_name",
            "client_email",
            "client_phone",
            "client_address",
            "client_company",
            "quote_number",
            "invoice_number",
            "subtotal",
            "discount",
            "tax",
            "total",
            "paid_amount",
            "balance_due",
            "created_at",
            "updated_at",
        ]

    def calculate_items(
        self,
        items_data,
    ):

        subtotal = Decimal("0.00")
        discount_total = Decimal("0.00")
        tax_total = Decimal("0.00")

        processed = []

        for item in items_data:

            quantity = Decimal(
                str(
                    item.get(
                        "quantity",
                        1,
                    )
                )
            )

            unit_price = Decimal(
                str(
                    item.get(
                        "unit_price",
                        0,
                    )
                )
            )

            discount = Decimal(
                str(
                    item.get(
                        "discount",
                        0,
                    )
                )
            )

            tax_rate = Decimal(
                str(
                    item.get(
                        "tax_rate",
                        0,
                    )
                )
            )

            if quantity <= 0 or unit_price < 0 or discount < 0 or tax_rate < 0:
                raise serializers.ValidationError(
                    "Item values cannot be negative and quantity must be greater than zero."
                )

            gross = (
                quantity
                * unit_price
            )

            if discount > gross:
                raise serializers.ValidationError({
                    "items": "An item discount cannot exceed its line amount."
                })

            taxable = max(
                Decimal("0.00"),
                gross - discount,
            )

            tax_amount = (
                taxable
                * tax_rate
                / Decimal("100")
            )

            amount = (
                taxable
                + tax_amount
            )

            item["amount"] = amount

            subtotal += gross
            discount_total += discount
            tax_total += tax_amount

            processed.append(item)

        total = (
            subtotal
            - discount_total
            + tax_total
        )

        return (
            processed,
            subtotal,
            discount_total,
            tax_total,
            total,
        )

    def create(self, validated_data):

        items_data = validated_data.pop(
            "items",
            [],
        )

        (
            items_data,
            subtotal,
            discount,
            tax,
            total,
        ) = self.calculate_items(
            items_data
        )

        invoice = Invoice.objects.create(
            **validated_data,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            balance_due=total,
        )

        for item_data in items_data:

            InvoiceItem.objects.create(
                invoice=invoice,
                **item_data,
            )

        return invoice

    def update(
        self,
        instance,
        validated_data,
    ):

        items_data = validated_data.pop(
            "items",
            None,
        )

        if items_data is not None:

            (
                items_data,
                subtotal,
                discount,
                tax,
                total,
            ) = self.calculate_items(
                items_data
            )

            instance.subtotal = subtotal
            instance.discount = discount
            instance.tax = tax
            instance.total = total

            instance.balance_due = max(
                Decimal("0.00"),
                total - instance.paid_amount,
            )

            instance.items.all().delete()

            for item_data in items_data:

                InvoiceItem.objects.create(
                    invoice=instance,
                    **item_data,
                )

        for attr, value in validated_data.items():
            setattr(
                instance,
                attr,
                value,
            )

        instance.save()

        return instance
