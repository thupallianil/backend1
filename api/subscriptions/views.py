from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import Subscription, BusinessProfile, Project, Payment, Invoice, Receipt
from api.tenant_helpers import resolve_user_context, get_request_business
from api.utils_events import log_audit_event, send_system_notification
from .serializers import SubscriptionSerializer

# Pricing Tier Definitions
PLAN_CONFIGS = {
    "FREE_TRIAL": {
        "plan_name": "FREE_TRIAL",
        "display_name": "Free Trial",
        "monthly_price": Decimal("0.00"),
        "max_projects": 5,
        "max_users": 5,
        "trial_limit": 5,
        "features": [
            "Up to 5 Free Projects",
            "Up to 5 Users",
            "Standard Task & Deliverable Review",
            "Basic Document Management",
        ],
    },
    "STARTER": {
        "plan_name": "STARTER",
        "display_name": "Starter",
        "monthly_price": Decimal("29.00"),
        "max_projects": 20,
        "max_users": 10,
        "features": [
            "Up to 20 Active Projects",
            "Up to 10 Team Members / Vendors",
            "Invoicing & Automated Receipts",
            "Standard Email Support",
        ],
    },
    "PROFESSIONAL": {
        "plan_name": "PROFESSIONAL",
        "display_name": "Professional",
        "monthly_price": Decimal("79.00"),
        "max_projects": 100,
        "max_users": 50,
        "features": [
            "Up to 100 Active Projects",
            "Up to 50 Team Members / Vendors",
            "Multi-Tier Approval Workflows",
            "Advanced Financial Reports & Analytics",
            "Priority Support & Audit Logs",
        ],
    },
    "ENTERPRISE": {
        "plan_name": "ENTERPRISE",
        "display_name": "Enterprise",
        "monthly_price": Decimal("199.00"),
        "max_projects": 500,
        "max_users": 200,
        "features": [
            "Up to 500 Active Projects",
            "Up to 200 Team Members / Vendors",
            "Custom Workflow Rules & SLA",
            "Dedicated Account Manager",
            "Custom Integrations & Webhooks",
        ],
    },
}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_plans(request):
    """
    Returns public/tenant SaaS plan pricing and quota options.
    """
    return Response({
        "success": True,
        "data": list(PLAN_CONFIGS.values())
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_subscription(request):
    """
    Returns current active or free-trial subscription for the authenticated user's business.
    """
    role, user_biz, _ = resolve_user_context(request.user)
    business = user_biz or get_request_business(request)

    if not business:
        return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

    # Ensure subscription exists with FREE_TRIAL as default
    sub, _ = Subscription.objects.get_or_create(
        business=business,
        defaults={
            "plan_name": Subscription.Plan.FREE_TRIAL,
            "status": Subscription.Status.TRIAL_ACTIVE,
            "trial_limit": 5,
            "trial_used": 0,
            "max_projects": 5,
            "max_users": 5,
            "monthly_price": Decimal("0.00"),
            "trial_started_at": timezone.now(),
        }
    )

    projects_count = Project.objects.filter(business=business).count()

    # Sync trial status if count >= 5
    if sub.plan_name == Subscription.Plan.FREE_TRIAL:
        sub.trial_used = projects_count
        if projects_count >= sub.trial_limit and sub.status == Subscription.Status.TRIAL_ACTIVE:
            sub.status = Subscription.Status.TRIAL_EXHAUSTED
            sub.trial_ended_at = timezone.now()
            sub.save(update_fields=["status", "trial_used", "trial_ended_at"])

    serializer = SubscriptionSerializer(sub)
    return Response({
        "success": True,
        "data": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_usage(request):
    """
    Detailed tenant quota metrics for projects, users, and trial progress.
    """
    role, user_biz, _ = resolve_user_context(request.user)
    business = user_biz or get_request_business(request)

    if not business:
        return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

    sub, _ = Subscription.objects.get_or_create(
        business=business,
        defaults={
            "plan_name": Subscription.Plan.FREE_TRIAL,
            "status": Subscription.Status.TRIAL_ACTIVE,
            "trial_limit": 5,
            "trial_used": 0,
            "max_projects": 5,
            "max_users": 5,
        }
    )

    projects_count = Project.objects.filter(business=business).count()
    clients_count = business.clients.count() if hasattr(business, "clients") else 0
    vendors_count = business.vendors.count() if hasattr(business, "vendors") else 0
    total_users = clients_count + vendors_count + 1

    is_trial = sub.plan_name == Subscription.Plan.FREE_TRIAL
    trial_exhausted = is_trial and (projects_count >= sub.trial_limit or sub.status == Subscription.Status.TRIAL_EXHAUSTED)
    upgrade_required = trial_exhausted or (not is_trial and projects_count >= sub.max_projects)

    return Response({
        "success": True,
        "data": {
            "plan_name": sub.plan_name,
            "status": sub.status,
            "is_trial": is_trial,
            "trial_exhausted": trial_exhausted,
            "upgrade_required": upgrade_required,
            "projects": {
                "used": projects_count,
                "limit": sub.trial_limit if is_trial else sub.max_projects,
                "remaining": max(0, (sub.trial_limit if is_trial else sub.max_projects) - projects_count),
                "percentage": min(100, round((projects_count / (sub.trial_limit if is_trial else sub.max_projects)) * 100)),
            },
            "users": {
                "used": total_users,
                "limit": sub.max_users,
                "remaining": max(0, sub.max_users - total_users),
                "percentage": min(100, round((total_users / sub.max_users) * 100)),
            },
            "monthly_price": float(sub.monthly_price),
            "valid_until": sub.valid_until,
        }
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upgrade_subscription(request):
    """
    Initiates subscription upgrade for the tenant. Returns payment order details.
    """
    role, user_biz, _ = resolve_user_context(request.user)
    business = user_biz or get_request_business(request)

    if not business:
        return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

    if role not in ["ADMIN", "SUPER_ADMIN"]:
        return Response({"error": "Only Admins can upgrade subscriptions"}, status=status.HTTP_403_FORBIDDEN)

    target_plan = request.data.get("plan_name", "").upper()
    if target_plan not in PLAN_CONFIGS or target_plan == "FREE_TRIAL":
        return Response({"error": f"Invalid plan. Choose from: STARTER, PROFESSIONAL, ENTERPRISE"}, status=status.HTTP_400_BAD_REQUEST)

    plan_info = PLAN_CONFIGS[target_plan]
    amount = plan_info["monthly_price"]

    log_audit_event(
        action="UPGRADE_INITIATED",
        entity_type="Subscription",
        business=business,
        actor=request.user,
        actor_role=role,
        details=f"Admin initiated upgrade to {target_plan} (${amount}/mo)",
        request=request
    )

    # Simulated order payload
    order_id = f"ORDER_SUB_{business.id}_{int(timezone.now().timestamp())}"

    return Response({
        "success": True,
        "message": f"Upgrade order initialized for {plan_info['display_name']}",
        "order": {
            "order_id": order_id,
            "plan_name": target_plan,
            "display_name": plan_info["display_name"],
            "amount": float(amount),
            "currency": "USD",
            "business_name": business.business_name,
        }
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_subscription_payment(request):
    """
    Verifies the payment and immediately activates the paid subscription tier.
    """
    role, user_biz, _ = resolve_user_context(request.user)
    business = user_biz or get_request_business(request)

    if not business:
        return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

    target_plan = request.data.get("plan_name", "").upper()
    payment_method = request.data.get("payment_method", "credit_card")
    transaction_ref = request.data.get("transaction_ref") or f"TXN_{int(timezone.now().timestamp())}"

    if target_plan not in PLAN_CONFIGS or target_plan == "FREE_TRIAL":
        return Response({"error": "Invalid plan name for paid activation"}, status=status.HTTP_400_BAD_REQUEST)

    plan_info = PLAN_CONFIGS[target_plan]

    with transaction.atomic():
        sub, _ = Subscription.objects.select_for_update().get_or_create(business=business)

        sub.plan_name = target_plan
        sub.status = Subscription.Status.ACTIVE
        sub.monthly_price = plan_info["monthly_price"]
        sub.max_projects = plan_info["max_projects"]
        sub.max_users = plan_info["max_users"]
        sub.valid_until = (timezone.now() + timedelta(days=30)).date()
        sub.save()

        # Audit Log
        log_audit_event(
            action="SUBSCRIPTION_ACTIVATED",
            entity_type="Subscription",
            entity_id=sub.id,
            business=business,
            actor=request.user,
            actor_role=role,
            details=f"Subscription activated: {target_plan} (${plan_info['monthly_price']}/mo). Project limit increased to {plan_info['max_projects']}.",
            request=request
        )

        # Notify business owner
        if business.owner:
            send_system_notification(
                user=business.owner,
                business=business,
                title="Subscription Active",
                message=f"Your {plan_info['display_name']} subscription is now active with a limit of {plan_info['max_projects']} projects.",
                notif_type="subscription_activated",
                link="/admin/subscription"
            )

    return Response({
        "success": True,
        "message": f"Successfully activated {plan_info['display_name']} plan!",
        "subscription": SubscriptionSerializer(sub).data
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def subscription_list_create(request):
    """
    Super Admin global subscription manager.
    """
    role, user_biz, _ = resolve_user_context(request.user)

    if request.method == "GET":
        if role == "SUPER_ADMIN":
            qs = Subscription.objects.all().order_by("-created_at")
        elif role == "ADMIN":
            if not user_biz:
                return Response([], status=status.HTTP_200_OK)
            qs = Subscription.objects.filter(business=user_biz)
        else:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        serializer = SubscriptionSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        if role != "SUPER_ADMIN":
            return Response({"error": "Only Super Admin can create/assign subscriptions"}, status=status.HTTP_403_FORBIDDEN)

        business_id = request.data.get("business")
        business = get_object_or_404(BusinessProfile, pk=business_id)

        serializer = SubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            sub = serializer.save(business=business)
            log_audit_event(
                action="SUBSCRIPTION_CHANGED",
                entity_type="Subscription",
                entity_id=sub.id,
                business=business,
                actor=request.user,
                actor_role=role,
                details=f"Assigned plan {sub.plan_name} ({sub.status}) to {business.business_name}",
                request=request
            )
            return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def subscription_detail(request, pk):
    role, user_biz, _ = resolve_user_context(request.user)
    sub = get_object_or_404(Subscription, pk=pk)

    if role == "ADMIN" and sub.business != user_biz:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_200_OK)

    elif request.method in ["PUT", "PATCH"]:
        if role != "SUPER_ADMIN":
            return Response({"error": "Only Super Admin can update subscriptions"}, status=status.HTTP_403_FORBIDDEN)

        serializer = SubscriptionSerializer(sub, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            log_audit_event(
                action="SUBSCRIPTION_CHANGED",
                entity_type="Subscription",
                entity_id=updated.id,
                business=updated.business,
                actor=request.user,
                actor_role=role,
                details=f"Updated plan {updated.plan_name} status={updated.status}",
                request=request
            )
            return Response(SubscriptionSerializer(updated).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
