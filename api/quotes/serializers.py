from decimal import Decimal

from rest_framework import serializers

from api.models import Quote, QuoteItem


class QuoteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteItem
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


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, required=False)

    client_name = serializers.CharField(
        source="client.name",
        read_only=True,
    )

    class Meta:
        model = Quote
        fields = [
            "id",
            "client",
            "client_name",
            "quote_number",
            "issue_date",
            "expiry_date",
            "status",
            "items",
            "notes",
            "terms",
            "subtotal",
            "discount",
            "tax",
            "total",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "client_name",
            "quote_number",
            "issue_date",
            "expiry_date",
            "subtotal",
            "discount",
            "tax",
            "total",
            "created_at",
            "updated_at",
        ]

    @staticmethod
    def calculate_items(items_data):
        subtotal = discount_total = tax_total = Decimal("0.00")
        for item in items_data:
            quantity = Decimal(str(item.get("quantity", 1)))
            unit_price = Decimal(str(item.get("unit_price", 0)))
            discount = Decimal(str(item.get("discount", 0)))
            tax_rate = Decimal(str(item.get("tax_rate", 0)))
            if quantity <= 0 or unit_price < 0 or discount < 0 or tax_rate < 0:
                raise serializers.ValidationError(
                    "Item values cannot be negative and quantity must be greater than zero."
                )
            gross = quantity * unit_price
            if discount > gross:
                raise serializers.ValidationError(
                    {"items": "An item discount cannot exceed its line amount."}
                )
            taxable = gross - discount
            tax_amount = taxable * tax_rate / Decimal("100")
            item["amount"] = taxable + tax_amount
            subtotal += gross
            discount_total += discount
            tax_total += tax_amount
        return subtotal, discount_total, tax_total, subtotal - discount_total + tax_total

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        subtotal, discount, tax, total = self.calculate_items(items_data)
        quote = Quote.objects.create(
            **validated_data,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
        )

        for item_data in items_data:
            QuoteItem.objects.create(
                quote=quote,
                **item_data,
            )

        return quote

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if items_data is not None:
            subtotal, discount, tax, total = self.calculate_items(items_data)
            instance.subtotal = subtotal
            instance.discount = discount
            instance.tax = tax
            instance.total = total
            instance.save(update_fields=["subtotal", "discount", "tax", "total", "updated_at"])
            instance.items.all().delete()

            for item_data in items_data:
                QuoteItem.objects.create(
                    quote=instance,
                    **item_data,
                )

        return instance
