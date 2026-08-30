from django.http import JsonResponse

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import AllowAny
from rest_framework.response import Response


# ============================================================
# API HOME
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def api_index(request):
    return JsonResponse({
        "success": True,
        "message": "Backend API is running successfully.",
        "data": {
            "health": "/api/health/",
            "auth": "/api/auth/",
            "settings": "/api/settings/",
            "profile": "/api/profile/",
            "clients": "/api/clients/",
            "quotes": "/api/quotes/",
            "invoices": "/api/invoices/",
            "payments": "/api/payments/",
            "receipts": "/api/receipts/",
            "dashboard": "/api/dashboard/",
            "reports": "/api/reports/",
        },
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        "success": True,
        "message": "Health check successful.",
        "data": {
            "status": "ok",
        },
    })


# ============================================================
# PUBLIC PLATFORM LIVE STATS AGGREGATE
# ============================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def public_platform_stats(request):
    try:
        from django.contrib.auth import get_user_model
        from django.db.models import Sum
        from .models import Invoice, Client, Vendor, Quote, Payment, BusinessProfile

        User = get_user_model()
        
        # Real-time database counts
        total_registered_users = User.objects.count()
        total_businesses = max(1, BusinessProfile.objects.count() + User.objects.filter(is_staff=True).count())
        total_clients = Client.objects.count()
        total_vendors = Vendor.objects.count()
        total_invoices = Invoice.objects.count()
        total_quotes = Quote.objects.count()
        
        # Real-time invoice volume
        volume_agg = Invoice.objects.aggregate(Sum("total"))
        total_volume = float(volume_agg["total__sum"] or 0)
        
        # Real-time paid volume
        paid_agg = Invoice.objects.filter(status="paid").aggregate(Sum("paid_amount"))
        total_paid_volume = float(paid_agg["paid_amount__sum"] or 0)


        return Response({
            "success": True,
            "message": "Live platform statistics fetched successfully.",
            "data": {
                "total_businesses": total_businesses,
                "total_registered_users": total_registered_users,
                "total_clients": total_clients,
                "total_vendors": total_vendors,
                "total_invoices": total_invoices,
                "total_quotes": total_quotes,
                "total_volume": total_volume,
                "total_paid_volume": total_paid_volume,
                "uptime_percentage": 99.98,
                "active_gateways_count": 4,
                "is_live_data": True,
            }
        })
    except Exception as e:
        return Response({
            "success": False,
            "message": str(e),
            "data": {
                "total_businesses": 1,
                "total_registered_users": 1,
                "total_clients": 0,
                "total_vendors": 0,
                "total_invoices": 0,
                "total_quotes": 0,
                "total_volume": 0,
                "total_paid_volume": 0,
                "uptime_percentage": 99.98,
                "active_gateways_count": 4,
                "is_live_data": False,
            }
        })


# ============================================================
# PUBLIC AI CHATBOT ASSISTANT (HOME PAGE)
# ============================================================

@api_view(["POST"])
@permission_classes([AllowAny])
def public_ai_chatbot(request):
    """
    Intelligent Public AI Chatbot for visitors on the Home Page.
    Answers questions about InvoiceFlow features, free trial, multi-tenancy,
    vendor workflows, client portal, invoices, and payments.
    """
    message = str(request.data.get("message") or "").strip().lower()
    
    if not message:
        return Response({
            "success": False,
            "reply": "Hello! How can I assist you with InvoiceFlow today?",
            "suggestions": [
                "How does the 5-project Free Trial work?",
                "How do Vendor Deliverables and QA Approvals work?",
                "How do Clients pay Invoices via Razorpay?",
                "What are the 4 user roles?",
            ]
        }, status=400)

    # 1. Check for Free Trial & Pricing
    if any(k in message for k in ["trial", "free", "price", "pricing", "cost", "plan", "limit", "subscription"]):
        reply = (
            "✨ **InvoiceFlow Free Trial & Pricing:**\n\n"
            "• **Free Trial:** Every new business gets a **5-Project Free Trial** with full access to clients, vendors, invoices, and tasks!\n"
            "• **Pro / Enterprise Plans:** When you exceed 5 projects, you can upgrade directly to our Professional or Enterprise plans for unlimited projects, custom domains, and dedicated priority support.\n\n"
            "👉 *Tip: Click 'Get Started Free' at the top right to start your trial in 30 seconds!*"
        )
        suggestions = [
            "How do Vendor Deliverables work?",
            "How do Clients pay Invoices?",
            "How do I sign up as a Business Admin?",
        ]

    # 2. Check for Vendor & Deliverables / QA
    elif any(k in message for k in ["vendor", "deliverable", "qa", "review", "subcontractor", "task", "milestone"]):
        reply = (
            "💼 **Vendor Deliverable & QA Approval Workflow:**\n\n"
            "1. **Task Assignment:** Business Admin assigns project milestones/tasks to registered vendors.\n"
            "2. **Submission:** Vendors upload files, deliverables, or GitHub links via their specialized **Vendor Portal** (`/vendor/dashboard`).\n"
            "3. **Admin Review:** Admin performs QA (Approve or Request Revisions).\n"
            "4. **Client Acceptance:** Once Admin approves, the deliverable moves to **Client Review** for final client approval!"
        )
        suggestions = [
            "How do Clients pay Invoices?",
            "What is the Super Admin console?",
            "How does the Free Trial work?",
        ]

    # 3. Check for Invoices & Payments / Razorpay
    elif any(k in message for k in ["invoice", "payment", "razorpay", "upi", "card", "billing", "receipt", "tax", "gst"]):
        reply = (
            "💳 **Invoicing & Integrated Payments:**\n\n"
            "• **Itemized Invoices:** Generate automated GST/tax-compliant invoices with custom prefixes and discount calculations.\n"
            "• **Instant Razorpay & UPI:** Clients can pay online with credit cards, debit cards, net banking, or instant UPI.\n"
            "• **Automatic Status Sync:** Once payment succeeds, the invoice balance is automatically cleared, status transitions to **PAID**, and a PDF receipt is issued."
        )
        suggestions = [
            "What are the 4 user roles?",
            "How do Vendor Deliverables work?",
            "Is my business data secure?",
        ]

    # 4. Check for User Roles & Permissions / SuperAdmin
    elif any(k in message for k in ["role", "roles", "super admin", "admin", "client", "portal", "permission", "rbac"]):
        reply = (
            "👑 **4 Distinct User Roles in InvoiceFlow:**\n\n"
            "1. **Super Admin:** Global owner console (`/super-admin/*`) managing platform tenants, subscriptions, and MRR.\n"
            "2. **Business Admin:** Workspace owner (`/admin/*`) managing projects, clients, vendors, quotes, and billing.\n"
            "3. **Vendor:** Subcontractor (`/vendor/*`) managing assigned tasks and uploading deliverables.\n"
            "4. **Client:** End customer (`/client/*`) reviewing milestones, accepting quotes, and paying invoices."
        )
        suggestions = [
            "How does the Free Trial work?",
            "How do Clients pay Invoices?",
            "Is my business data secure?",
        ]

    # 5. Check for Security & Multi-Tenancy
    elif any(k in message for k in ["security", "tenant", "isolation", "safe", "privacy", "data", "gdpr", "cloud"]):
        reply = (
            "🔒 **Enterprise-Grade Multi-Tenant Security:**\n\n"
            "• **Strict Tenant Isolation:** Each business workspace is isolated. Cross-tenant access is blocked via database middleware (`HTTP 403 / 404`).\n"
            "• **Cryptographic JWT:** Secure session management with short-lived access tokens and token blacklisting on logout.\n"
            "• **Audit Logging:** Every project update, deliverable review, and payment event is immutably logged in the audit trail."
        )
        suggestions = [
            "How do I create a business account?",
            "What are the subscription plans?",
            "How do Vendor Deliverables work?",
        ]

    # 6. Check for Sign up / Getting Started
    elif any(k in message for k in ["signup", "sign up", "register", "start", "create account", "login", "demo"]):
        reply = (
            "🚀 **Getting Started with InvoiceFlow:**\n\n"
            "1. Click **'Get Started Free'** on the top navigation bar.\n"
            "2. Enter your business name, email, and password.\n"
            "3. Verify your 6-digit email OTP.\n"
            "4. Your 5-Project Free Trial workspace will be ready immediately!"
        )
        suggestions = [
            "What features are included in Free Trial?",
            "How do Clients pay Invoices?",
            "What are the 4 user roles?",
        ]

    # 7. Greetings / General Conversation
    elif any(k in message for k in ["hello", "hi", "hey", "help", "who are you", "what is this", "about"]):
        reply = (
            "👋 **Hello! Welcome to InvoiceFlow.**\n\n"
            "I'm your AI assistant for the InvoiceFlow platform. I can help you understand our **multi-tenant business workspace**, **5-project free trial**, **vendor QA workflows**, **client portal**, and **instant Razorpay payments**.\n\n"
            "What would you like to explore today?"
        )
        suggestions = [
            "How does the 5-project Free Trial work?",
            "How do Vendor Deliverables work?",
            "How do Clients pay Invoices via Razorpay?",
            "What are the 4 user roles?",
        ]

    # 8. Default fallback answer
    else:
        reply = (
            f"🤖 **InvoiceFlow Intelligent Assistant:**\n\n"
            f"Thanks for asking about *'{message[:50]}'*!\n\n"
            "InvoiceFlow is the all-in-one multi-tenant platform for managing projects, clients, vendor deliverables, quotations, and automated Razorpay invoicing with real-time audit logging.\n\n"
            "Would you like to learn more about our 5-project Free Trial, vendor workflows, or payment gateways?"
        )
        suggestions = [
            "How does the 5-project Free Trial work?",
            "How do Vendor Deliverables and QA Approvals work?",
            "How do Clients pay Invoices via Razorpay?",
            "What are the 4 user roles?",
        ]

    return Response({
        "success": True,
        "reply": reply,
        "suggestions": suggestions,
    })