from rest_framework import serializers


class DashboardReportSerializer(serializers.Serializer):
    clients = serializers.IntegerField()
    active_clients = serializers.IntegerField()

    quotes = serializers.IntegerField()
    accepted_quotes = serializers.IntegerField()

    invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    pending_invoices = serializers.IntegerField()
    overdue_invoices = serializers.IntegerField()

    invoice_total = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    paid_amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    outstanding_amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    payments = serializers.IntegerField()
    receipts = serializers.IntegerField()

    payment_total = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    revenue_monthly = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )
    
    payment_monthly = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )
    
    tax_breakdown = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )


class SalesReportSerializer(serializers.Serializer):
    months = serializers.ListField(
        child=serializers.DictField()
    )

    total_sales = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    total_subtotal = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    total_tax = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    total_discount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )


class PaymentReportSerializer(serializers.Serializer):
    months = serializers.ListField(
        child=serializers.DictField()
    )

    total_paid = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    total_outstanding = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    successful_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()


class TaxReportSerializer(serializers.Serializer):
    total_tax = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    monthly = serializers.ListField(
        child=serializers.DictField()
    )

    note = serializers.CharField()


class ClientReportSerializer(serializers.Serializer):
    total_clients = serializers.IntegerField()
    active_clients = serializers.IntegerField()
    inactive_clients = serializers.IntegerField()

    top_clients = serializers.ListField(
        child=serializers.DictField()
    )


class ProfitLossReportSerializer(serializers.Serializer):
    revenue = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    collected = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    outstanding = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    discounts = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    tax = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    expenses = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    net_profit = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    note = serializers.CharField()