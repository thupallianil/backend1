from django.contrib import admin
from .models import (
    BusinessProfile,
    AppSettings,
    Client,
    Vendor,
    Quote,
    QuoteItem,
    Invoice,
    InvoiceItem,
    Payment,
    Receipt,
    Ticket,
    TicketMessage,
    Notification,
)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "company_name",
        "category",
        "email",
        "phone",
        "tax_number",
        "is_active",
        "created_at",
    ]
    list_filter = ["category", "is_active", "created_at"]
    search_fields = [
        "name",
        "company_name",
        "email",
        "phone",
        "tax_number",
        "city",
    ]
    ordering = ["-created_at"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "company_name", "email", "phone", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "company_name", "email", "phone"]


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ["business_name", "owner", "email", "phone", "currency", "created_at"]
    search_fields = ["business_name", "owner__username", "email"]


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ["business", "currency", "timezone", "created_at"]


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ["quote_number", "business", "client", "status", "total", "issue_date"]
    list_filter = ["status", "issue_date"]
    search_fields = ["quote_number", "client__name", "client__company_name"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "business", "client", "status", "total", "paid_amount", "balance_due", "issue_date"]
    list_filter = ["status", "issue_date"]
    search_fields = ["invoice_number", "client__name", "client__company_name"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "business", "invoice", "amount", "method", "status", "created_at"]
    list_filter = ["status", "method", "created_at"]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "business", "invoice", "amount", "issued_date"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["ticket_number", "subject", "client", "category", "priority", "status", "created_at"]
    list_filter = ["category", "priority", "status", "created_at"]
    search_fields = ["ticket_number", "subject", "client__name"]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ["ticket", "sender", "sender_role", "created_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "type", "is_read", "created_at"]
    list_filter = ["is_read", "type", "created_at"]
