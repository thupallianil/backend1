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

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "category"]),
            models.Index(fields=["business", "is_active"]),
        ]

    def __str__(self):
        return self.company_name or self.name


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


