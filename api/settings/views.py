from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from api.models import AppSettings, BusinessProfile
from .serializers import SettingsSerializer


# ============================================================
# HELPER: get (or auto-create) business for the logged-in user
# ============================================================

def get_or_create_business(user):
    business = BusinessProfile.objects.filter(owner=user).first()
    if not business:
        business = BusinessProfile.objects.first()
    if not business:
        business = BusinessProfile.objects.create(
            owner=user,
            business_name=user.username or user.email or "My Business",
            email=user.email or "",
        )
    return business


# ============================================================
# SETTINGS DATA BUILDER
# Returns only what is stored in the DB – no hardcoded defaults.
# ============================================================

def settings_data(settings_obj):
    business   = settings_obj.business
    extra      = dict(settings_obj.extra_settings  or {})
    payment_st = dict(settings_obj.payment_settings or {})
    email_st   = dict(settings_obj.email_settings   or {})
    pdf_st     = dict(settings_obj.pdf_settings     or {})
    trans_st   = dict(settings_obj.translations     or {})

    return {
        "id": settings_obj.id,

        # -------------------------------------------------- BUSINESS
        "business": {
            "companyName":          business.business_name         or "",
            "businessName":         business.business_name         or "",
            "legalName":            business.legal_name            or "",
            "businessType":         business.business_type         or "",
            "registrationNumber":   business.registration_number   or "",
            "taxNumber":            business.tax_number            or "",
            "email":                business.email                 or "",
            "phone":                business.phone                 or "",
            "website":              business.website               or "",
            "address":              business.address               or "",
            "city":                 business.city                  or "",
            "state":                business.state                 or "",
            "postalCode":           business.postal_code           or "",
            "country":              business.country               or "",
            "currency":             business.currency              or "",
            "timezone":             business.timezone              or "",
            "extraInfo":            extra.get("business_extraInfo", ""),
            "logo":                 extra.get("business_logo",      ""),
            "logoUrl":              extra.get("business_logoUrl",   ""),
            "vatNumber":            extra.get("business_vatNumber", ""),
            "abnNumber":            extra.get("business_abnNumber", ""),
        },

        # -------------------------------------------------- GENERAL
        "general": {
            "language":             settings_obj.language          or "",
            "currency":             settings_obj.currency          or "",
            "dateFormat":           settings_obj.date_format       or "",
            "timezone":             settings_obj.timezone          or "",
            "financialYear":        extra.get("general_financialYear",     ""),
            "financialYearStart":   extra.get("general_financialYearStart",""),
            "financialYearEnd":     extra.get("general_financialYearEnd",  ""),
            "predefinedItems":      extra.get("general_predefinedItems",   ""),
            "currencySymbol":       extra.get("general_currencySymbol",    payment_st.get("currencySymbol", "")),
            "thousandSeparator":    extra.get("general_thousandSeparator", payment_st.get("thousandSeparator", ",")),
            "decimalSeparator":     extra.get("general_decimalSeparator",  payment_st.get("decimalSeparator", ".")),
            "decimalPlaces":        extra.get("general_decimalPlaces",     payment_st.get("decimalPlaces", 2)),
        },

        # -------------------------------------------------- QUOTATION
        "quotation": {
            "prefix":               settings_obj.quotation_prefix          or "",
            "suffix":               extra.get("quote_suffix",              ""),
            "autoIncrement":        extra.get("quote_autoIncrement",       True),
            "nextNumber":           settings_obj.next_quotation_number     or 1,
            "validityDays":         settings_obj.quotation_validity_days   or 0,
            "quotesValidFor":       settings_obj.quotation_validity_days   or 0,
            "hideAdjust":           extra.get("quote_hideAdjust",          False),
            "terms":                settings_obj.quotation_terms           or "",
            "defaultTerms":         settings_obj.quotation_terms           or "",
            "footer":               settings_obj.quotation_notes           or "",
            "defaultFooter":        settings_obj.quotation_notes           or "",
            "selectedTemplate":     settings_obj.quotation_template        or "",
            "customCss":            extra.get("quote_customCss",           ""),
            "showAcceptButton":     extra.get("quote_showAcceptButton",    True),
            "showDeclineButton":    extra.get("quote_showDeclineButton",   True),
            "defaultTaxRate":       float(settings_obj.default_tax_rate    or 0),
            "defaultDiscountType":  extra.get("quote_defaultDiscountType", "amount"),
        },

        # -------------------------------------------------- INVOICE
        "invoice": {
            "prefix":               settings_obj.invoice_prefix            or "",
            "suffix":               extra.get("invoice_suffix",            ""),
            "autoIncrement":        extra.get("invoice_autoIncrement",     True),
            "nextNumber":           settings_obj.next_invoice_number       or 1,
            "dueDays":              settings_obj.invoice_due_days          or 0,
            "defaultDueDays":       settings_obj.invoice_due_days          or 0,
            "hideAdjust":           extra.get("invoice_hideAdjust",        False),
            "terms":                settings_obj.invoice_terms             or "",
            "defaultTerms":         settings_obj.invoice_terms             or "",
            "footer":               settings_obj.invoice_notes             or "",
            "defaultFooter":        settings_obj.invoice_notes             or "",
            "selectedTemplate":     settings_obj.invoice_template          or "",
            "customCss":            extra.get("invoice_customCss",         ""),
            "noticeViewed":         extra.get("invoice_noticeViewed",      True),
            "noticePaid":           extra.get("invoice_noticePaid",        True),
            "defaultTaxRate":       float(settings_obj.default_tax_rate    or 0),
            "defaultDiscountType":  extra.get("invoice_defaultDiscountType","amount"),
            "autoRoundOff":         extra.get("invoice_autoRoundOff",      True),
        },

        # -------------------------------------------------- PAYMENTS
        "payments": {
            "currency":             settings_obj.currency                  or "",
            "currencySymbol":       payment_st.get("currencySymbol",       ""),
            "currencyPosition":     payment_st.get("currencyPosition",     "left"),
            "thousandSeparator":    payment_st.get("thousandSeparator",    ","),
            "decimalSeparator":     payment_st.get("decimalSeparator",     "."),
            "decimalPlaces":        payment_st.get("decimalPlaces",        2),
            "paymentPage":          payment_st.get("paymentPage",          ""),
            "paymentPageFooter":    payment_st.get("paymentPageFooter",    ""),
            "bankDetailsText":      payment_st.get("bankDetailsText",      ""),
            "genericPaymentText":   payment_st.get("genericPaymentText",   ""),
            "onlineEnabled":        settings_obj.online_payment_enabled,
            "razorpayEnabled":      payment_st.get("razorpayEnabled",      False),
            "razorpayKeyId":        payment_st.get("razorpayKeyId",        ""),
            "razorpaySecretKey":    "",  # never expose secret
            "razorpayEmail":        payment_st.get("razorpayEmail",        ""),
            "upiEnabled":           payment_st.get("upiEnabled",           False),
            "upiId":                payment_st.get("upiId",                ""),
            "bankTransferEnabled":  payment_st.get("bankTransferEnabled",  False),
            "bankName":             payment_st.get("bankName",             ""),
            "accountName":          payment_st.get("accountName",          ""),
            "accountNumber":        payment_st.get("accountNumber",        ""),
            "ifscCode":             payment_st.get("ifscCode",             payment_st.get("ifsc", "")),
            "cashEnabled":          payment_st.get("cashEnabled",          False),
            "cashBranch":           payment_st.get("cashBranch",           ""),
            "cashReceiptNote":      payment_st.get("cashReceiptNote",      ""),
            "cashInstructions":     payment_st.get("cashInstructions",     ""),
        },

        # -------------------------------------------------- EMAILS
        "emails": {
            "emailAddress":             email_st.get("emailAddress",             ""),
            "fromEmail":                email_st.get("emailAddress",             ""),
            "emailName":                email_st.get("emailName",                settings_obj.email_from_name or ""),
            "fromName":                 email_st.get("emailName",                settings_obj.email_from_name or ""),
            "bccOnClientEmails":        email_st.get("bccOnClientEmails",        False),
            "quoteSubject":             email_st.get("quoteSubject",             ""),
            "quoteContent":             email_st.get("quoteContent",             ""),
            "quoteButtonText":          email_st.get("quoteButtonText",          ""),
            "invoiceSubject":           email_st.get("invoiceSubject",           ""),
            "invoiceContent":           email_st.get("invoiceContent",           ""),
            "invoiceButtonText":        email_st.get("invoiceButtonText",        ""),
            "paymentReceivedSubject":   email_st.get("paymentReceivedSubject",   ""),
            "paymentReceivedContent":   email_st.get("paymentReceivedContent",   ""),
            "reminderDays":             email_st.get("reminderDays",             []),
            "reminderSubject":          email_st.get("reminderSubject",          ""),
            "reminderContent":          email_st.get("reminderContent",          ""),
            "emailFooterText":          email_st.get("emailFooterText",          ""),
            "smtpHost":                 email_st.get("smtpHost",                 ""),
            "smtpPort":                 email_st.get("smtpPort",                 587),
        },
        "email": {
            "enabled":   settings_obj.email_enabled,
            "fromName":  settings_obj.email_from_name or "",
            **email_st,
        },

        # -------------------------------------------------- TAX
        "tax": {
            "enabled":       settings_obj.tax_enabled,
            "taxName":       settings_obj.tax_name        or "",
            "defaultRate":   float(settings_obj.default_tax_rate or 0),
            "cgstRate":      extra.get("tax_cgstRate",    0),
            "sgstRate":      extra.get("tax_sgstRate",    0),
            "igstRate":      extra.get("tax_igstRate",    0),
            "hsnSacEnabled": extra.get("tax_hsnSacEnabled", False),
            "gstNumber":     extra.get("tax_gstNumber",   business.tax_number or ""),
        },

        # -------------------------------------------------- TRANSLATE
        "translate": {
            "quoteLabel":        trans_st.get("quoteLabel",       ""),
            "quoteLabelPlural":  trans_st.get("quoteLabelPlural", ""),
            "invoiceLabel":      trans_st.get("invoiceLabel",     ""),
            "invoiceLabelPlural":trans_st.get("invoiceLabelPlural",""),
            "labelHrsQty":       trans_st.get("labelHrsQty",     ""),
            "labelService":      trans_st.get("labelService",     ""),
            "labelRatePrice":    trans_st.get("labelRatePrice",   ""),
            "labelAdjust":       trans_st.get("labelAdjust",      ""),
            "labelSubTotal":     trans_st.get("labelSubTotal",    ""),
            "labelDiscount":     trans_st.get("labelDiscount",    ""),
            "labelTotal":        trans_st.get("labelTotal",       ""),
            "labelTotalDue":     trans_st.get("labelTotalDue",    ""),
            **trans_st,
        },
        "translations": trans_st,

        # -------------------------------------------------- PDF
        "pdf": {
            "pageSize":    pdf_st.get("pageSize",   "A4"),
            "accentColor": pdf_st.get("accentColor",""),
            "showLogo":    settings_obj.pdf_show_logo,
            "showSignature": settings_obj.pdf_show_signature,
            "footerText":  pdf_st.get("footerText", ""),
            **pdf_st,
        },

        # -------------------------------------------------- EXTRAS
        "extras": { **extra },

        # -------------------------------------------------- LICENSE
        "license": {
            "companyName":  extra.get("license_companyName",  ""),
            "purchaseCode": extra.get("license_purchaseCode", ""),
            "licenseKey":   settings_obj.license_key          or "",
            "expiryDate":   extra.get("license_expiryDate",   ""),
            "status":       "active" if settings_obj.license_active else "inactive",
        },
    }


# ============================================================
# API VIEW: GET / PUT / PATCH /api/settings/
# ============================================================

@extend_schema(tags=["Settings"], request=SettingsSerializer)
@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def settings_detail(request):
    business     = get_or_create_business(request.user)
    settings_obj, _ = AppSettings.objects.get_or_create(business=business)

    # -------------------------------------------------------- GET
    if request.method == "GET":
        return Response({
            "success": True,
            "message": "Settings retrieved successfully.",
            "data":    settings_data(settings_obj),
        })

    # -------------------------------------------------------- PUT / PATCH
    try:
        data       = request.data or {}
        extra      = dict(settings_obj.extra_settings   or {})
        payment_st = dict(settings_obj.payment_settings or {})
        email_st   = dict(settings_obj.email_settings   or {})
        pdf_st     = dict(settings_obj.pdf_settings     or {})
        trans_st   = dict(settings_obj.translations     or {})

        # ---- BUSINESS ----
        bd = data.get("business")
        if isinstance(bd, dict):
            b_name = str(bd.get("businessName") or bd.get("companyName") or business.business_name or "My Business").strip()
            if b_name:
                business.business_name = b_name

            if "legalName" in bd: business.legal_name = str(bd.get("legalName") or "")[:255]
            if "businessType" in bd: business.business_type = str(bd.get("businessType") or "")[:100]
            if "registrationNumber" in bd: business.registration_number = str(bd.get("registrationNumber") or "")[:100]
            if "taxNumber" in bd: business.tax_number = str(bd.get("taxNumber") or "")[:100]
            if "email" in bd: business.email = str(bd.get("email") or "").strip()[:254]
            if "phone" in bd: business.phone = str(bd.get("phone") or "").strip()[:30]
            if "website" in bd:
                web_val = str(bd.get("website") or "").strip()
                if web_val and not web_val.startswith("http://") and not web_val.startswith("https://"):
                    web_val = "https://" + web_val
                business.website = web_val[:200]
            if "address" in bd: business.address = str(bd.get("address") or "")
            if "city" in bd: business.city = str(bd.get("city") or "")[:100]
            if "state" in bd: business.state = str(bd.get("state") or "")[:100]
            if "postalCode" in bd: business.postal_code = str(bd.get("postalCode") or "")[:20]
            if "country" in bd: business.country = str(bd.get("country") or "India")[:100]
            if "currency" in bd: business.currency = str(bd.get("currency") or "INR")[:10]
            if "timezone" in bd: business.timezone = str(bd.get("timezone") or "Asia/Kolkata")[:100]

            extra_info = bd.get("extraInfo") or bd.get("extraBusinessInfo") or ""
            if extra_info or "extraInfo" in bd or "extraBusinessInfo" in bd:
                extra["business_extraInfo"] = str(extra_info)

            for k in ["logo", "logoUrl", "vatNumber", "abnNumber"]:
                if k in bd:
                    extra[f"business_{k}"] = str(bd[k] or "")

            business.save()

        # ---- GENERAL ----
        gd = data.get("general")
        if isinstance(gd, dict):
            if "language"  in gd: settings_obj.language    = str(gd["language"] or "en")[:20]
            if "currency"  in gd: settings_obj.currency    = str(gd["currency"] or "INR")[:10]
            if "dateFormat" in gd: settings_obj.date_format = str(gd["dateFormat"] or "DD/MM/YYYY")[:50]
            if "timezone"  in gd: settings_obj.timezone    = str(gd["timezone"] or "Asia/Kolkata")[:100]
            for k in ["financialYear","financialYearStart","financialYearEnd",
                      "predefinedItems","currencySymbol","thousandSeparator",
                      "decimalSeparator","decimalPlaces"]:
                if k in gd:
                    extra[f"general_{k}"] = gd[k]

        # ---- QUOTATION ----
        qd = data.get("quotation") or data.get("quotes")
        if isinstance(qd, dict):
            if "prefix" in qd: settings_obj.quotation_prefix = str(qd["prefix"] or "QUO")[:20]
            if "nextNumber" in qd:
                try: settings_obj.next_quotation_number = int(qd["nextNumber"])
                except: pass
            if "validityDays" in qd:
                try: settings_obj.quotation_validity_days = int(qd["validityDays"])
                except: pass
            if "quotesValidFor" in qd:
                try: settings_obj.quotation_validity_days = int(qd["quotesValidFor"])
                except: pass
            if "terms" in qd or "defaultTerms" in qd:
                terms_val = qd.get("defaultTerms") if "defaultTerms" in qd else qd.get("terms")
                settings_obj.quotation_terms = str(terms_val or "")
            if "footer" in qd or "defaultFooter" in qd or "notes" in qd:
                footer_val = qd.get("defaultFooter") if "defaultFooter" in qd else (qd.get("footer") if "footer" in qd else qd.get("notes"))
                settings_obj.quotation_notes = str(footer_val or "")
            if "selectedTemplate" in qd: settings_obj.quotation_template = str(qd["selectedTemplate"] or "template1")[:50]
            for k in ["suffix","autoIncrement","hideAdjust","customCss",
                      "showAcceptButton","showDeclineButton","defaultDiscountType"]:
                if k in qd: extra[f"quote_{k}"] = qd[k]

        # ---- INVOICE ----
        inv = data.get("invoice") or data.get("invoices")
        if isinstance(inv, dict):
            if "prefix" in inv: settings_obj.invoice_prefix = str(inv["prefix"] or "INV")[:20]
            if "nextNumber" in inv:
                try: settings_obj.next_invoice_number = int(inv["nextNumber"])
                except: pass
            if "dueDays" in inv:
                try: settings_obj.invoice_due_days = int(inv["dueDays"])
                except: pass
            if "defaultDueDays" in inv:
                try: settings_obj.invoice_due_days = int(inv["defaultDueDays"])
                except: pass
            if "terms" in inv or "defaultTerms" in inv:
                terms_val = inv.get("defaultTerms") if "defaultTerms" in inv else inv.get("terms")
                settings_obj.invoice_terms = str(terms_val or "")
            if "footer" in inv or "defaultFooter" in inv or "notes" in inv:
                footer_val = inv.get("defaultFooter") if "defaultFooter" in inv else (inv.get("footer") if "footer" in inv else inv.get("notes"))
                settings_obj.invoice_notes = str(footer_val or "")
            if "selectedTemplate" in inv: settings_obj.invoice_template = str(inv["selectedTemplate"] or "template1")[:50]
            for k in ["suffix","autoIncrement","hideAdjust","customCss",
                      "noticeViewed","noticePaid","defaultDiscountType","autoRoundOff"]:
                if k in inv: extra[f"invoice_{k}"] = inv[k]

        # ---- PAYMENTS ----
        pay = data.get("payments") or data.get("payment")
        if isinstance(pay, dict):
            if "onlineEnabled" in pay: settings_obj.online_payment_enabled = bool(pay["onlineEnabled"])
            if "currency"      in pay: settings_obj.currency = str(pay["currency"] or "INR")[:10]
            SECRET_KEYS = {"razorpaySecretKey","stripeSecretKey","paypalClientSecret"}
            for k, v in pay.items():
                if k in SECRET_KEYS and (v == "" or v is None): continue
                payment_st[k] = v

        # ---- TAX ----
        tx = data.get("tax")
        if isinstance(tx, dict):
            if "enabled"     in tx: settings_obj.tax_enabled      = bool(tx["enabled"])
            if "taxName"     in tx: settings_obj.tax_name         = str(tx["taxName"] or "GST")[:50]
            if "defaultRate" in tx:
                try: settings_obj.default_tax_rate = float(tx["defaultRate"])
                except: pass
            for k in ["cgstRate","sgstRate","igstRate","hsnSacEnabled","gstNumber"]:
                if k in tx: extra[f"tax_{k}"] = tx[k]

        # ---- EMAILS ----
        em = data.get("emails") or data.get("email")
        if isinstance(em, dict):
            if "enabled"   in em: settings_obj.email_enabled    = bool(em["enabled"])
            if "emailName" in em: settings_obj.email_from_name  = str(em["emailName"] or "")[:100]
            if "fromName"  in em: settings_obj.email_from_name  = str(em["fromName"] or "")[:100]
            if em.get("password") == "": em.pop("password", None)
            email_st.update(em)

        # ---- TRANSLATE ----
        tr = data.get("translate") or data.get("translations")
        if isinstance(tr, dict):
            trans_st.update(tr)

        # ---- PDF ----
        pd_data = data.get("pdf")
        if isinstance(pd_data, dict):
            if "showLogo"      in pd_data: settings_obj.pdf_show_logo      = bool(pd_data["showLogo"])
            if "showSignature" in pd_data: settings_obj.pdf_show_signature = bool(pd_data["showSignature"])
            pdf_st.update(pd_data)

        # ---- EXTRAS ----
        ex = data.get("extras")
        if isinstance(ex, dict):
            extra.update(ex)

        # ---- LICENSE ----
        lic = data.get("license")
        if isinstance(lic, dict):
            key = lic.get("licenseKey") or lic.get("key")
            if key is not None:
                settings_obj.license_key    = str(key)[:255]
                settings_obj.license_active = bool(key)
            for k in ["companyName","purchaseCode","expiryDate"]:
                if k in lic: extra[f"license_{k}"] = str(lic[k] or "")

        # ---- PERSIST ----
        settings_obj.extra_settings   = extra
        settings_obj.payment_settings = payment_st
        settings_obj.email_settings   = email_st
        settings_obj.pdf_settings     = pdf_st
        settings_obj.translations     = trans_st
        settings_obj.save()

        return Response({
            "success": True,
            "message": "Settings updated successfully.",
            "data":    settings_data(settings_obj),
        })
    except Exception as exc:
        return Response({
            "success": False,
            "message": f"Unable to update settings: {str(exc)}",
        }, status=status.HTTP_400_BAD_REQUEST)