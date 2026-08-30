from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# ============================================================
# COMMON BASE MODEL
# ============================================================

class TimeStampedModel(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        abstract = True


# ============================================================
# BUSINESS PROFILE
# ============================================================

class BusinessProfile(TimeStampedModel):

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_profile",
    )

    # ========================================================
    # BUSINESS INFORMATION
    # ========================================================

    business_name = models.CharField(
        max_length=255,
        default="My Business",
    )

    legal_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    business_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # ========================================================
    # CONTACT
    # ========================================================

    email = models.EmailField(
        blank=True,
        default="",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    website = models.URLField(
        blank=True,
        default="",
    )

    # ========================================================
    # ADDRESS
    # ========================================================

    address = models.TextField(
        blank=True,
        default="",
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    country = models.CharField(
        max_length=100,
        default="India",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    # ========================================================
    # TAX
    # ========================================================

    tax_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # ========================================================
    # LOGO
    # ========================================================

    logo = models.ImageField(
        upload_to="business/logos/",
        blank=True,
        null=True,
    )

    # ========================================================
    # DEFAULTS
    # ========================================================

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    timezone = models.CharField(
        max_length=100,
        default="Asia/Kolkata",
    )

    is_active = models.BooleanField(
        default=True,
    )

    status = models.CharField(
        max_length=30,
        default="active",
    )

    class Meta:
        ordering = [
            "business_name"
        ]

    def __str__(self):
        return self.business_name


# ============================================================
# APPLICATION SETTINGS
# ============================================================

class AppSettings(TimeStampedModel):

    business = models.OneToOneField(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # ========================================================
    # GENERAL SETTINGS
    # ========================================================

    language = models.CharField(
        max_length=20,
        default="en",
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    date_format = models.CharField(
        max_length=50,
        default="DD/MM/YYYY",
    )

    timezone = models.CharField(
        max_length=100,
        default="Asia/Kolkata",
    )

    # ========================================================
    # QUOTATION SETTINGS
    # ========================================================

    quotation_prefix = models.CharField(
        max_length=30,
        default="QUO",
    )

    next_quotation_number = models.PositiveIntegerField(
        default=1,
    )

    quotation_validity_days = models.PositiveIntegerField(
        default=15,
    )

    quotation_terms = models.TextField(
        blank=True,
        default="",
    )

    quotation_notes = models.TextField(
        blank=True,
        default="",
    )

    # SEPARATE QUOTATION TEMPLATE

    quotation_template = models.CharField(
        max_length=50,
        default="template1",
    )

    # ========================================================
    # INVOICE SETTINGS
    # ========================================================

    invoice_prefix = models.CharField(
        max_length=30,
        default="INV",
    )

    next_invoice_number = models.PositiveIntegerField(
        default=1,
    )

    invoice_due_days = models.PositiveIntegerField(
        default=15,
    )

    invoice_terms = models.TextField(
        blank=True,
        default="",
    )

    invoice_notes = models.TextField(
        blank=True,
        default="",
    )

    # SEPARATE INVOICE TEMPLATE

    invoice_template = models.CharField(
        max_length=50,
        default="template1",
    )

    # ========================================================
    # PAYMENT SETTINGS
    # ========================================================

    online_payment_enabled = models.BooleanField(
        default=False,
    )

    payment_settings = models.JSONField(
        default=dict,
        blank=True,
    )

    # ========================================================
    # TAX SETTINGS
    # ========================================================

    tax_enabled = models.BooleanField(
        default=True,
    )

    tax_name = models.CharField(
        max_length=100,
        default="GST",
        blank=True,
    )

    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ========================================================
    # EMAIL SETTINGS
    # ========================================================

    email_enabled = models.BooleanField(
        default=False,
    )

    email_from_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    email_settings = models.JSONField(
        default=dict,
        blank=True,
    )

    # ========================================================
    # PDF SETTINGS
    # ========================================================

    pdf_show_logo = models.BooleanField(
        default=True,
    )

    pdf_show_signature = models.BooleanField(
        default=False,
    )

    pdf_settings = models.JSONField(
        default=dict,
        blank=True,
    )

    # ========================================================
    # RECEIPT SETTINGS
    # ========================================================

    receipt_prefix = models.CharField(
        max_length=30,
        default="REC",
    )

    next_receipt_number = models.PositiveIntegerField(
        default=1,
    )

    # ========================================================
    # EXTRA SETTINGS
    # ========================================================

    extra_settings = models.JSONField(
        default=dict,
        blank=True,
    )

    # ========================================================
    # TRANSLATIONS
    # ========================================================

    translations = models.JSONField(
        default=dict,
        blank=True,
    )

    # ========================================================
    # LICENSE
    # ========================================================

    license_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    license_active = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return (
            f"Settings - "
            f"{self.business.business_name}"
        )


# ============================================================
# CLIENT
# ============================================================

class Client(TimeStampedModel):

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="clients",
    )

    name = models.CharField(
        max_length=255,
    )

    company_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    address = models.TextField(
        blank=True,
        default="",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_records",
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

    def __str__(self):
        return self.name


# ============================================================
# QUOTE
# ============================================================

class Quote(TimeStampedModel):

    class Status(models.TextChoices):

        DRAFT = (
            "draft",
            "Draft",
        )

        SENT = (
            "sent",
            "Sent",
        )

        ACCEPTED = (
            "accepted",
            "Accepted",
        )

        REJECTED = (
            "rejected",
            "Rejected",
        )

        EXPIRED = (
            "expired",
            "Expired",
        )

        CONVERTED = (
            "converted",
            "Converted",
        )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="quotes",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="quotes",
    )

    quote_number = models.CharField(
        max_length=50,
    )

    issue_date = models.DateField(
        default=timezone.localdate,
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    terms = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "business",
                    "quote_number",
                ]
            ),
            models.Index(
                fields=[
                    "business",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return self.quote_number


# ============================================================
# QUOTE ITEM
# ============================================================

class QuoteItem(TimeStampedModel):

    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="items",
    )

    description = models.CharField(
        max_length=500,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = [
            "id"
        ]

    def save(self, *args, **kwargs):

        self.amount = (
            self.quantity * self.unit_price
        ) - self.discount

        if self.amount < 0:
            self.amount = Decimal("0.00")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.description


# ============================================================
# INVOICE
# ============================================================

class Invoice(TimeStampedModel):

    class Status(models.TextChoices):

        DRAFT = (
            "draft",
            "Draft",
        )

        SENT = (
            "sent",
            "Sent",
        )

        PARTIALLY_PAID = (
            "partially_paid",
            "Partially Paid",
        )

        PAID = (
            "paid",
            "Paid",
        )

        OVERDUE = (
            "overdue",
            "Overdue",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    quote = models.ForeignKey(
        Quote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    project = models.ForeignKey(
        "Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    invoice_number = models.CharField(
        max_length=50,
    )

    issue_date = models.DateField(
        default=timezone.localdate,
    )

    due_date = models.DateField(
        default=timezone.localdate,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    balance_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    terms = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "business",
                    "invoice_number",
                ]
            ),
            models.Index(
                fields=[
                    "business",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "business",
                    "due_date",
                ]
            ),
        ]

    def save(self, *args, **kwargs):

        if self.balance_due is None:
            self.balance_due = max(
                Decimal("0.00"),
                self.total - self.paid_amount,
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number


# ============================================================
# INVOICE ITEM
# ============================================================

class InvoiceItem(TimeStampedModel):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )

    description = models.CharField(
        max_length=500,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
    )

    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = [
            "id"
        ]

    def save(self, *args, **kwargs):

        self.amount = (
            self.quantity * self.unit_price
        ) - self.discount

        if self.amount < 0:
            self.amount = Decimal("0.00")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.description


# ============================================================
# PAYMENT
# ============================================================

class Payment(TimeStampedModel):

    class Method(models.TextChoices):

        CASH = (
            "cash",
            "Cash",
        )

        BANK = (
            "bank",
            "Bank Transfer",
        )

        UPI = (
            "upi",
            "UPI",
        )

        CARD = (
            "card",
            "Card",
        )

        ONLINE = (
            "online",
            "Online",
        )

        OTHER = (
            "other",
            "Other",
        )

    class Status(models.TextChoices):

        PENDING = (
            "pending",
            "Pending",
        )

        SUCCESS = (
            "success",
            "Success",
        )

        FAILED = (
            "failed",
            "Failed",
        )

        REFUNDED = (
            "refunded",
            "Refunded",
        )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    method = models.CharField(
        max_length=30,
        choices=Method.choices,
        default=Method.CASH,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    gateway_order_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    gateway_payment_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    gateway_signature = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "business",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "invoice",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"Payment #{self.id} - "
            f"{self.amount}"
        )


# ============================================================
# RECEIPT
# ============================================================

class Receipt(TimeStampedModel):

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="receipts",
    )

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="receipt",
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="receipts",
    )

    receipt_number = models.CharField(
        max_length=50,
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    issued_date = models.DateField(
        default=timezone.localdate,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "business",
                    "receipt_number",
                ]
            ),
        ]

    def __str__(self):
        return self.receipt_number


# ============================================================
# SUPPORT TICKET
# ============================================================

class Ticket(TimeStampedModel):

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Category(models.TextChoices):
        BILLING = "billing", "Billing & Payments"
        INVOICE = "invoice", "Invoice Inquiry"
        TECHNICAL = "technical", "Technical Support"
        ACCOUNT = "account", "Account & Access"
        FEATURE = "feature", "Feature Request"
        GENERAL = "general", "General Inquiry"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING_CLIENT = "waiting_client", "Waiting for Client"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tickets",
    )

    ticket_number = models.CharField(
        max_length=50,
        unique=True,
    )

    subject = models.CharField(
        max_length=255,
    )

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERAL,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
    )

    description = models.TextField()

    attachment = models.FileField(
        upload_to="tickets/attachments/",
        blank=True,
        null=True,
    )

    last_reply_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-last_reply_at", "-created_at"]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["ticket_number"]),
        ]

    def __str__(self):
        return f"[{self.ticket_number}] {self.subject}"


class TicketMessage(TimeStampedModel):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_messages",
    )

    sender_role = models.CharField(
        max_length=20,
        choices=[("admin", "Admin"), ("client", "Client")],
        default="client",
    )

    message = models.TextField()

    attachment = models.FileField(
        upload_to="tickets/replies/",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply on {self.ticket.ticket_number} by {self.sender.username}"


# ============================================================
# NOTIFICATION
# ============================================================

class Notification(TimeStampedModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    type = models.CharField(
        max_length=50,
        default="general",
    )

    link = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    is_read = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"


# ============================================================
# VENDOR
# ============================================================

class Vendor(TimeStampedModel):

    class Category(models.TextChoices):
        GOODS = "goods", "Goods & Materials"
        SERVICES = "services", "Services & Consulting"
        RAW_MATERIALS = "raw_materials", "Raw Materials"
        LOGISTICS = "logistics", "Logistics & Shipping"
        UTILITIES = "utilities", "Utilities & Rent"
        IT_SOFTWARE = "it_software", "IT & Software"
        CONTRACTOR = "contractor", "Contractor & Freelance"
        EQUIPMENT = "equipment", "Machinery & Equipment"
        OTHER = "other", "Other"

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="vendors",
    )

    name = models.CharField(
        max_length=255,
    )

    company_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GOODS,
    )

    tax_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    pan_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    address = models.TextField(
        blank=True,
        default="",
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    country = models.CharField(
        max_length=100,
        default="India",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    website = models.URLField(
        blank=True,
        default="",
    )

    bank_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    account_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    account_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    ifsc_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    upi_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    payment_terms = models.CharField(
        max_length=50,
        blank=True,
        default="Net 30",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_records",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "category"]),
            models.Index(fields=["business", "is_active"]),
        ]

    def __str__(self):
        return self.company_name or self.name


# ============================================================
# USER PROFILE & EXTENDED ROLE MODEL
# ============================================================

class UserProfile(TimeStampedModel):

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        VENDOR = "vendor", "Vendor"
        CLIENT = "client", "Client"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    avatar = models.ImageField(
        upload_to="profiles/avatars/",
        blank=True,
        null=True,
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_users",
    )

    client = models.ForeignKey(
        "Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_users",
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"



# ============================================================
# SIGNUP & PASSWORD RESET EMAIL VERIFICATION OTP
# ============================================================

class SignupVerificationOTP(TimeStampedModel):
    email = models.EmailField(
        db_index=True,
    )

    otp = models.CharField(
        max_length=6,
    )

    temp_data = models.JSONField(
        default=dict,
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "otp"]),
            models.Index(fields=["email", "expires_at"]),
        ]

    @property
    def otp_code(self):
        return self.otp

    def __str__(self):
        return f"OTP for {self.email} ({self.otp})"


class PasswordResetOTP(TimeStampedModel):
    email = models.EmailField(
        db_index=True,
    )

    otp = models.CharField(
        max_length=6,
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "otp"]),
            models.Index(fields=["email", "expires_at"]),
        ]

    @property
    def otp_code(self):
        return self.otp

    def __str__(self):
        return f"Reset OTP for {self.email} ({self.otp})"


# ============================================================
# PROJECT & MEMBERSHIP
# ============================================================

class Project(TimeStampedModel):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        REVISION_REQUIRED = "revision_required", "Revision Required"
        APPROVED = "approved", "Approved"
        CLIENT_REVIEW = "client_review", "Client Review"
        CLIENT_APPROVED = "client_approved", "Client Approved"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
    )

    title = models.CharField(
        max_length=255,
    )

    code = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    progress_percentage = models.PositiveIntegerField(
        default=0,
    )

    assigned_vendors = models.ManyToManyField(
        Vendor,
        through="ProjectMember",
        related_name="assigned_projects",
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["client", "status"]),
        ]

    def __str__(self):
        return f"[{self.code or self.id}] {self.title}"


class ProjectMember(TimeStampedModel):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )

    role = models.CharField(
        max_length=100,
        default="Assigned Vendor",
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = ("project", "vendor")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vendor.name} on {self.project.title}"


# ============================================================
# TASK & COMMENTS
# ============================================================

class Task(TimeStampedModel):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        REVISION_REQUIRED = "revision_required", "Revision Required"
        COMPLETED = "completed", "Completed"
        BLOCKED = "blocked", "Blocked"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    assigned_vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    progress_percentage = models.PositiveIntegerField(
        default=0,
    )

    estimated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    actual_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = ["due_date", "-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["assigned_vendor", "status"]),
            models.Index(fields=["business", "status"]),
        ]

    def __str__(self):
        return f"Task: {self.title} ({self.status})"


class TaskComment(TimeStampedModel):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_comments",
    )

    author_role = models.CharField(
        max_length=20,
        default="admin",
    )

    message = models.TextField()

    attachment = models.FileField(
        upload_to="tasks/comments/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"


# ============================================================
# DELIVERABLE & MULTI-TIER APPROVALS
# ============================================================

class Deliverable(TimeStampedModel):

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        ADMIN_REVIEW = "admin_review", "Under Admin Review"
        REVISION_REQUIRED = "revision_required", "Revision Required"
        ADMIN_APPROVED = "admin_approved", "Admin Approved"
        CLIENT_REVIEW = "client_review", "Under Client Review"
        CLIENT_CHANGES_REQUESTED = "client_changes_requested", "Client Changes Requested"
        CLIENT_APPROVED = "client_approved", "Client Approved"
        COMPLETED = "completed", "Completed"

    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverables",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="deliverables",
    )

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="deliverables",
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="deliverables",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_deliverables",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    version = models.CharField(
        max_length=20,
        default="v1.0",
    )

    file_attachment = models.FileField(
        upload_to="deliverables/files/",
        null=True,
        blank=True,
    )

    external_url = models.URLField(
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )

    admin_notes = models.TextField(
        blank=True,
        default="",
    )

    client_notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["business", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.version}) - {self.status}"


class DeliverableApproval(TimeStampedModel):

    class Action(models.TextChoices):
        APPROVE = "approve", "Approved"
        REJECT = "reject", "Rejected / Revision Required"
        REQUEST_CHANGES = "request_changes", "Changes Requested"

    deliverable = models.ForeignKey(
        Deliverable,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deliverable_reviews",
    )

    reviewer_role = models.CharField(
        max_length=20,
        choices=[("admin", "Admin"), ("client", "Client")],
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )

    feedback = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reviewer_role.upper()} {self.action} on {self.deliverable.title}"


# ============================================================
# DOCUMENTS
# ============================================================

class Document(TimeStampedModel):

    class AccessLevel(models.TextChoices):
        ADMIN_ONLY = "admin_only", "Admin Only"
        PROJECT_MEMBERS = "project_members", "Project Members & Vendor"
        CLIENT_VISIBLE = "client_visible", "Client & Project Members"
        PUBLIC_TENANT = "public_tenant", "All Tenant Users"

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )

    title = models.CharField(
        max_length=255,
    )

    file = models.FileField(
        upload_to="documents/",
    )

    file_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    file_size = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    access_level = models.CharField(
        max_length=30,
        choices=AccessLevel.choices,
        default=AccessLevel.PROJECT_MEMBERS,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "access_level"]),
            models.Index(fields=["project"]),
        ]

    def __str__(self):
        return self.title


# ============================================================
# MESSAGES & ROLE COMMUNICATION
# ============================================================

class Message(TimeStampedModel):

    class ConversationType(models.TextChoices):
        DIRECT_ADMIN_VENDOR = "direct_admin_vendor", "Admin <-> Vendor"
        DIRECT_ADMIN_CLIENT = "direct_admin_client", "Admin <-> Client"
        PROJECT_ROOM = "project_room", "Project Team Room"

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_messages",
    )

    conversation_type = models.CharField(
        max_length=40,
        choices=ConversationType.choices,
        default=ConversationType.DIRECT_ADMIN_VENDOR,
    )

    content = models.TextField()

    attachment = models.FileField(
        upload_to="messages/attachments/",
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["business", "conversation_type"]),
            models.Index(fields=["sender", "is_read"]),
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"Msg from {self.sender.username} ({self.conversation_type})"


# ============================================================
# AUDIT LOGGING
# ============================================================

class AuditLog(TimeStampedModel):

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
    )

    actor_role = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    action = models.CharField(
        max_length=100,
    )

    entity_type = models.CharField(
        max_length=100,
    )

    entity_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    details = models.TextField(
        blank=True,
        default="",
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.action} by {self.actor_role or 'System'}"


# ============================================================
# SUBSCRIPTION & SAAS PLANS
# ============================================================

class Subscription(TimeStampedModel):

    class Plan(models.TextChoices):
        FREE_TRIAL = "FREE_TRIAL", "Free Trial"
        STARTER = "STARTER", "Starter"
        PROFESSIONAL = "PROFESSIONAL", "Professional"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    class Status(models.TextChoices):
        TRIAL_ACTIVE = "TRIAL_ACTIVE", "Trial Active"
        TRIAL_EXHAUSTED = "TRIAL_EXHAUSTED", "Trial Exhausted"
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past Due"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    business = models.OneToOneField(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan_name = models.CharField(
        max_length=50,
        choices=Plan.choices,
        default=Plan.FREE_TRIAL,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.TRIAL_ACTIVE,
    )

    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    billing_cycle = models.CharField(
        max_length=20,
        default="monthly",
    )

    max_projects = models.PositiveIntegerField(
        default=5,
    )

    max_users = models.PositiveIntegerField(
        default=5,
    )

    trial_limit = models.PositiveIntegerField(
        default=5,
    )

    trial_used = models.PositiveIntegerField(
        default=0,
    )

    trial_started_at = models.DateTimeField(
        null=True,
        blank=True,
        default=timezone.now,
    )

    trial_ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    valid_until = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "status"]),
            models.Index(fields=["plan_name", "status"]),
        ]

    def __str__(self):
        return f"{self.business.business_name} - {self.plan_name} ({self.status})"


# ============================================================
# AUTOMATIC SUBSCRIPTION SIGNALS
# ============================================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=BusinessProfile)
def auto_create_business_free_trial(sender, instance, created, **kwargs):
    """
    Ensures every newly created Business/Tenant automatically receives a FREE_TRIAL subscription.
    """
    if created:
        Subscription.objects.get_or_create(
            business=instance,
            defaults={
                "plan_name": Subscription.Plan.FREE_TRIAL,
                "status": Subscription.Status.TRIAL_ACTIVE,
                "trial_limit": 5,
                "trial_used": 0,
                "max_projects": 5,
                "max_users": 5,
                "monthly_price": Decimal("0.00"),
            }
        )

# ============================================================
# GLOBAL PLATFORM SETTINGS (SUPER ADMIN ONLY)
# ============================================================

class GlobalPlatformSettings(TimeStampedModel):
    # 1. PLATFORM & BRANDING
    platform_name = models.CharField(max_length=255, default="Enterprise Multi-Tenant SaaS Platform")
    logo_url = models.CharField(max_length=500, blank=True, default="")
    favicon_url = models.CharField(max_length=500, blank=True, default="")
    support_email = models.EmailField(default="support@system.io")
    support_phone = models.CharField(max_length=50, blank=True, default="+1 800 555 0199")
    default_currency = models.CharField(max_length=10, default="USD")
    default_timezone = models.CharField(max_length=100, default="UTC")
    date_format = models.CharField(max_length=50, default="YYYY-MM-DD")
    platform_description = models.TextField(blank=True, default="Comprehensive multi-tenant business and project workspace management.")

    # 2. FREE TRIAL
    trial_enabled = models.BooleanField(default=True)
    trial_limit = models.PositiveIntegerField(default=5)
    trial_type = models.CharField(max_length=50, default="PROJECTS")
    action_after_limit = models.CharField(max_length=50, default="REQUIRE_UPGRADE")

    # 3. SUBSCRIPTION PLANS (Stored as structured JSON)
    plans_config = models.JSONField(default=dict, blank=True)

    # 4. PAYMENT & PLATFORM BILLING
    platform_payment_gateway = models.CharField(max_length=100, default="Razorpay / Stripe")
    merchant_account_status = models.CharField(max_length=100, default="Connected & Active")
    settlement_status = models.CharField(max_length=100, default="Operational")
    billing_currency = models.CharField(max_length=10, default="USD")
    webhook_status = models.CharField(max_length=100, default="Live (200 OK)")

    # 5. EMAIL / SMTP
    smtp_provider = models.CharField(max_length=100, default="SendGrid / Custom SMTP")
    smtp_host = models.CharField(max_length=255, default="smtp.sendgrid.net")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255, default="apikey")
    from_email = models.EmailField(default="no-reply@system.io")
    from_name = models.CharField(max_length=255, default="Platform System Notifications")
    smtp_encryption = models.CharField(max_length=20, default="TLS")

    # 6. NOTIFICATIONS (Stored as structured JSON)
    notification_events = models.JSONField(default=dict, blank=True)

    # 7. SECURITY & ACCESS
    min_password_length = models.PositiveIntegerField(default=8)
    require_special_char = models.BooleanField(default=True)
    session_timeout_minutes = models.PositiveIntegerField(default=120)
    login_attempt_limit = models.PositiveIntegerField(default=5)
    invitation_expiry_days = models.PositiveIntegerField(default=7)
    enforce_mfa = models.BooleanField(default=False)

    # 8. SYSTEM DEFAULTS
    default_business_currency = models.CharField(max_length=10, default="USD")
    default_business_timezone = models.CharField(max_length=100, default="UTC")
    default_business_plan = models.CharField(max_length=50, default="FREE_TRIAL")
    default_business_status = models.CharField(max_length=30, default="active")

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        if created or not obj.plans_config:
            obj.plans_config = {
                "STARTER": {"name": "Starter", "price": 29, "max_projects": 20, "max_users": 10, "is_active": True},
                "PROFESSIONAL": {"name": "Professional", "price": 79, "max_projects": 100, "max_users": 50, "is_active": True},
                "ENTERPRISE": {"name": "Enterprise", "price": 199, "max_projects": 500, "max_users": 200, "is_active": True},
            }
            obj.notification_events = {
                "new_business": {"in_app": True, "email": True},
                "trial_exhausted": {"in_app": True, "email": True},
                "subscription_upgrade": {"in_app": True, "email": True},
                "subscription_payment": {"in_app": True, "email": True},
                "payment_failure": {"in_app": True, "email": True},
                "business_suspended": {"in_app": True, "email": True},
                "security_events": {"in_app": True, "email": True},
            }
            obj.save()
        return obj


