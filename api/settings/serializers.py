from rest_framework import serializers


# ============================================================
# GENERAL
# ============================================================

class GeneralSettingsSerializer(serializers.Serializer):

    language = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    currency = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
    )

    dateFormat = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )

    timezone = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )


# ============================================================
# BUSINESS
# ============================================================

class BusinessSettingsSerializer(serializers.Serializer):

    companyName = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    legalName = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )

    businessType = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    registrationNumber = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    taxNumber = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )

    website = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
    )

    address = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    state = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    postalCode = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    currency = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
    )

    timezone = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )


# ============================================================
# QUOTATION
# ============================================================

class QuotationSettingsSerializer(serializers.Serializer):

    prefix = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )

    nextNumber = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    validityDays = serializers.IntegerField(
        required=False,
        min_value=0,
    )

    defaultTaxRate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=0,
        max_value=100,
    )

    defaultDiscountType = serializers.ChoiceField(
        choices=[
            ("amount", "Amount"),
            ("percentage", "Percentage"),
        ],
        required=False,
    )

    defaultFooter = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    defaultTerms = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    selectedTemplate = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )


# ============================================================
# INVOICE
# ============================================================

class InvoiceSettingsSerializer(serializers.Serializer):

    prefix = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )

    nextNumber = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    defaultDueDays = serializers.IntegerField(
        required=False,
        min_value=0,
    )

    defaultTaxRate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=0,
        max_value=100,
    )

    defaultDiscountType = serializers.ChoiceField(
        choices=[
            ("amount", "Amount"),
            ("percentage", "Percentage"),
        ],
        required=False,
    )

    autoRoundOff = serializers.BooleanField(
        required=False,
    )

    defaultFooter = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    defaultTerms = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    selectedTemplate = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )


# ============================================================
# PAYMENTS
# ============================================================

class PaymentSettingsSerializer(serializers.Serializer):

    currency = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
    )

    onlineEnabled = serializers.BooleanField(
        required=False,
    )

    razorpayEnabled = serializers.BooleanField(
        required=False,
    )

    razorpayKeyId = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    razorpaySecretKey = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    stripeEnabled = serializers.BooleanField(
        required=False,
    )

    stripePublishableKey = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    stripeSecretKey = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    paypalEnabled = serializers.BooleanField(
        required=False,
    )

    paypalClientId = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    paypalClientSecret = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    upiEnabled = serializers.BooleanField(
        required=False,
    )

    upiId = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    bankTransferEnabled = serializers.BooleanField(
        required=False,
    )

    bankName = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    accountName = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    accountNumber = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    ifscCode = serializers.CharField(
        required=False,
        allow_blank=True,
    )


# ============================================================
# TAX
# ============================================================

class TaxSettingsSerializer(serializers.Serializer):

    enabled = serializers.BooleanField(
        required=False,
    )

    taxName = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    defaultRate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
    )


# ============================================================
# EMAIL
# ============================================================

class EmailSettingsSerializer(serializers.Serializer):

    enabled = serializers.BooleanField(
        required=False,
    )

    smtpHost = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    smtpPort = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=65535,
    )

    username = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    password = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    encryption = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    fromName = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    fromEmail = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    replyTo = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    invoiceSubject = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    quoteSubject = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    paymentSubject = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    signature = serializers.CharField(
        required=False,
        allow_blank=True,
    )


# ============================================================
# PDF
# ============================================================

class PDFSettingsSerializer(serializers.Serializer):

    pageSize = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    orientation = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    showLogo = serializers.BooleanField(
        required=False,
    )

    showBusinessAddress = serializers.BooleanField(
        required=False,
    )

    showTaxDetails = serializers.BooleanField(
        required=False,
    )

    showPaymentDetails = serializers.BooleanField(
        required=False,
    )

    showSignature = serializers.BooleanField(
        required=False,
    )

    footerText = serializers.CharField(
        required=False,
        allow_blank=True,
    )


# ============================================================
# EXTRAS
# ============================================================

class ExtrasSettingsSerializer(serializers.Serializer):

    darkMode = serializers.BooleanField(
        required=False,
    )

    notifications = serializers.BooleanField(
        required=False,
    )

    emailNotifications = serializers.BooleanField(
        required=False,
    )

    overdueNotifications = serializers.BooleanField(
        required=False,
    )

    paymentNotifications = serializers.BooleanField(
        required=False,
    )

    maintenanceMode = serializers.BooleanField(
        required=False,
    )


# ============================================================
# LICENSE
# ============================================================

class LicenseSettingsSerializer(serializers.Serializer):

    key = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    status = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    expiry = serializers.CharField(
        required=False,
        allow_blank=True,
    )


# ============================================================
# TRANSLATIONS
# ============================================================

class TranslationSettingsSerializer(serializers.Serializer):

    language = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
    )

    labels = serializers.DictField(
        required=False,
    )


# ============================================================
# COMPLETE SETTINGS
# ============================================================

class SettingsSerializer(serializers.Serializer):

    general = GeneralSettingsSerializer(
        required=False,
    )

    business = BusinessSettingsSerializer(
        required=False,
    )

    quotation = QuotationSettingsSerializer(
        required=False,
    )

    invoice = InvoiceSettingsSerializer(
        required=False,
    )

    payments = PaymentSettingsSerializer(
        required=False,
    )

    tax = TaxSettingsSerializer(
        required=False,
    )

    email = EmailSettingsSerializer(
        required=False,
    )

    pdf = PDFSettingsSerializer(
        required=False,
    )

    extras = ExtrasSettingsSerializer(
        required=False,
    )

    license = LicenseSettingsSerializer(
        required=False,
    )

    translations = TranslationSettingsSerializer(
        required=False,
    )