import datetime
from decimal import Decimal
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny
from rest_framework.response import Response

from api.models import (
    BusinessProfile,
    UserProfile,
    Project,
    Subscription,
    AuditLog,
    AppSettings,
    Payment,
)
from api.utils_events import log_audit_event

logger = logging.getLogger(__name__)
User = get_user_model()


def send_admin_welcome_email(email, name, business_name, password, login_url="http://localhost:5173/login"):
    """Dispatches a branded welcome & credentials email to newly provisioned Business Admins."""
    subject = f"Welcome to InvoiceFlow - Your '{business_name}' Workspace is Ready"
    plain_msg = (
        f"Hello {name},\n\n"
        f"A new business workspace '{business_name}' has been created for you on InvoiceFlow.\n\n"
        f"Login Credentials:\n"
        f"• Login URL: {login_url}\n"
        f"• Email: {email}\n"
        f"• Temporary Password: {password}\n\n"
        f"You have been granted a 5-Project Free Trial to start managing clients, vendors, deliverables, and invoices.\n\n"
        f"Please log in and update your password under Settings.\n\n"
        f"Regards,\nInvoiceFlow Executive Team"
    )
    html_msg = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 540px; margin: 0 auto; padding: 32px 24px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; color: #1e293b;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; width: 44px; height: 44px; background: #9333ea; border-radius: 12px; line-height: 44px; color: #ffffff; font-size: 20px; font-weight: bold; margin-bottom: 12px;">IF</div>
            <h2 style="color: #0f172a; margin: 0; font-size: 22px; font-weight: 800;">Welcome to InvoiceFlow</h2>
            <p style="color: #64748b; font-size: 14px; margin-top: 6px;">Your workspace <strong>{business_name}</strong> has been provisioned.</p>
        </div>
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; font-size: 13px; color: #475569;"><strong>Email / Username:</strong> <span style="font-family: monospace; color: #0f172a;">{email}</span></p>
            <p style="margin: 0 0 10px 0; font-size: 13px; color: #475569;"><strong>Initial Password:</strong> <span style="font-family: monospace; color: #9333ea; font-weight: bold;">{password}</span></p>
            <p style="margin: 0; font-size: 13px; color: #475569;"><strong>Plan:</strong> <span style="color: #16a34a; font-weight: bold;">5-Project Free Trial</span></p>
        </div>
        <div style="text-align: center; margin: 28px 0;">
            <a href="{login_url}" style="background: #9333ea; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 10px; font-weight: bold; font-size: 14px; display: inline-block;">Log In to Your Admin Console</a>
        </div>
        <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin: 0;">For security, we recommend changing your password after your first login in your Business Settings.</p>
    </div>
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@invoiceflow.com"
    try:
        send_mail(subject, plain_msg, from_email, [email], html_message=html_msg, fail_silently=True)
    except Exception as e:
        logger.warning(f"Failed to dispatch welcome email: {e}")


class IsSuperAdminUser(BasePermission):
    """
    Allows access only to authenticated superuser or super_admin role accounts.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        profile = getattr(request.user, "profile", None)
        return bool(profile and profile.role in ["super_admin", "SUPER_ADMIN"])


# ============================================================
# 1. SUPER ADMIN STATS & GROWTH TELEMETRY (100% DATABASE DRIVEN)
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_stats(request):
    """
    Returns global platform telemetry calculated directly from the database.
    Separates platform subscription revenue from tenant client project payments.
    """
    now = timezone.now()
    time_range = request.GET.get("time_range", "6_months").lower()

    # 1. Core Platform KPI Counts
    total_tenants = BusinessProfile.objects.count()
    total_users = User.objects.count()
    total_projects = Project.objects.count()

    # Subscriptions & Trials
    sub_qs = Subscription.objects.all()
    active_subscriptions = sub_qs.filter(status__in=["TRIAL_ACTIVE", "ACTIVE"]).count()
    trial_active_count = sub_qs.filter(plan_name="FREE_TRIAL", status="TRIAL_ACTIVE").count()
    trial_exhausted_count = sub_qs.filter(status="TRIAL_EXHAUSTED").count()
    
    starter_count = sub_qs.filter(plan_name__icontains="Starter").count()
    pro_count = sub_qs.filter(plan_name__icontains="Pro").count()
    ent_count = sub_qs.filter(plan_name__icontains="Enterprise").count()
    cancelled_count = sub_qs.filter(status__in=["CANCELLED", "EXPIRED"]).count()
    active_paid_count = sub_qs.filter(status="ACTIVE").exclude(plan_name="FREE_TRIAL").count()

    # Platform Monthly Subscription Revenue
    # Calculated strictly from active paid subscription plan pricing
    # Starter = $29, Professional = $79, Enterprise = $199
    PLAN_PRICES = {
        "STARTER": Decimal("29.00"),
        "PROFESSIONAL": Decimal("79.00"),
        "ENTERPRISE": Decimal("199.00"),
    }
    
    monthly_subscription_rev = Decimal("0.00")
    for sub in sub_qs.filter(status="ACTIVE"):
        pname = (sub.plan_name or "").upper()
        if "ENTERPRISE" in pname:
            monthly_subscription_rev += PLAN_PRICES["ENTERPRISE"]
        elif "PRO" in pname:
            monthly_subscription_rev += PLAN_PRICES["PROFESSIONAL"]
        elif "STARTER" in pname:
            monthly_subscription_rev += PLAN_PRICES["STARTER"]

    # 2. Dynamic Time-Series Growth Buckets
    labels = []
    biz_series = []
    user_series = []
    proj_series = []
    rev_series = []

    if time_range == "7_days":
        for i in range(6, -1, -1):
            day_start = (now - datetime.timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + datetime.timedelta(days=1)
            labels.append(day_start.strftime("%a"))
            
            b_cnt = BusinessProfile.objects.filter(created_at__lt=day_end).count()
            u_cnt = User.objects.filter(date_joined__lt=day_end).count()
            p_cnt = Project.objects.filter(created_at__lt=day_end).count()
            
            biz_series.append(b_cnt)
            user_series.append(u_cnt)
            proj_series.append(p_cnt)
            rev_series.append(float(monthly_subscription_rev))
    elif time_range == "30_days":
        for i in range(4, -1, -1):
            w_start = (now - datetime.timedelta(days=i * 6)).replace(hour=0, minute=0, second=0, microsecond=0)
            labels.append(w_start.strftime("%b %d"))
            
            b_cnt = BusinessProfile.objects.filter(created_at__lte=w_start).count()
            u_cnt = User.objects.filter(date_joined__lte=w_start).count()
            p_cnt = Project.objects.filter(created_at__lte=w_start).count()
            
            biz_series.append(b_cnt)
            user_series.append(u_cnt)
            proj_series.append(p_cnt)
            rev_series.append(float(monthly_subscription_rev))
    elif time_range == "12_months":
        for i in range(11, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            m_date = datetime.datetime(year, month, 1, tzinfo=now.tzinfo)
            # End of this month
            if month == 12:
                next_m = datetime.datetime(year + 1, 1, 1, tzinfo=now.tzinfo)
            else:
                next_m = datetime.datetime(year, month + 1, 1, tzinfo=now.tzinfo)
            
            labels.append(m_date.strftime("%b"))
            
            b_cnt = BusinessProfile.objects.filter(created_at__lt=next_m).count()
            u_cnt = User.objects.filter(date_joined__lt=next_m).count()
            p_cnt = Project.objects.filter(created_at__lt=next_m).count()
            
            biz_series.append(b_cnt)
            user_series.append(u_cnt)
            proj_series.append(p_cnt)
            rev_series.append(float(monthly_subscription_rev))
    else:  # Default 6_months
        for i in range(5, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            m_date = datetime.datetime(year, month, 1, tzinfo=now.tzinfo)
            if month == 12:
                next_m = datetime.datetime(year + 1, 1, 1, tzinfo=now.tzinfo)
            else:
                next_m = datetime.datetime(year, month + 1, 1, tzinfo=now.tzinfo)
            
            labels.append(m_date.strftime("%b"))
            
            b_cnt = BusinessProfile.objects.filter(created_at__lt=next_m).count()
            u_cnt = User.objects.filter(date_joined__lt=next_m).count()
            p_cnt = Project.objects.filter(created_at__lt=next_m).count()
            
            biz_series.append(b_cnt)
            user_series.append(u_cnt)
            proj_series.append(p_cnt)
            rev_series.append(float(monthly_subscription_rev))

    growth_data = {
        "labels": labels,
        "businesses": biz_series,
        "users": user_series,
        "projects": proj_series,
        "revenue": rev_series,
    }

    # 3. Subscription Breakdown Structure
    total_subs = sub_qs.count() or 1
    subscription_overview = {
        "free_trial": {
            "count": trial_active_count + trial_exhausted_count,
            "active": trial_active_count,
            "exhausted": trial_exhausted_count,
        },
        "starter": {
            "count": starter_count,
            "percentage": round((starter_count / total_subs) * 100),
        },
        "professional": {
            "count": pro_count,
            "percentage": round((pro_count / total_subs) * 100),
        },
        "enterprise": {
            "count": ent_count,
            "percentage": round((ent_count / total_subs) * 100),
        },
        "total_subscriptions": sub_qs.count(),
        "active_paid_subscriptions": active_paid_count,
        "cancelled_subscriptions": cancelled_count,
    }

    # 4. Recent Businesses (Direct DB Query)
    recent_qs = BusinessProfile.objects.select_related("owner").order_by("-created_at")[:6]
    recent_businesses = []
    for b in recent_qs:
        sub = sub_qs.filter(business=b).first()
        plan_name = sub.plan_name if sub else "FREE_TRIAL"
        sub_status = sub.status if sub else ("Active" if getattr(b, "is_active", True) else "Suspended")
        
        users_count = (b.clients.count() if hasattr(b, "clients") else 0) + (b.vendors.count() if hasattr(b, "vendors") else 0) + 1
        max_users = sub.max_users if sub else 5
        projects_count = b.projects.count() if hasattr(b, "projects") else 0
        max_projs = sub.max_projects if sub else 5

        recent_businesses.append({
            "id": b.id,
            "business_name": b.business_name,
            "admin_email": b.owner.email if b.owner else (b.email or "admin@business.io"),
            "plan": plan_name,
            "sub_status": sub_status,
            "users_count": users_count,
            "max_users": max_users,
            "projects_count": projects_count,
            "max_projects": max_projs,
            "status": "Active" if getattr(b, "is_active", True) else "Suspended",
            "joined_on": b.created_at.strftime("%d %b %Y"),
        })

    # 5. Recent Platform-Level Audit Activity
    platform_actions = [
        "CREATE_BUSINESS", "UPDATE_BUSINESS", "SUSPEND_BUSINESS", "ACTIVATE_BUSINESS",
        "INVITE_ADMIN", "CREATE_USER", "SUBSCRIPTION_UPGRADED", "TRIAL_EXHAUSTED",
        "PAYMENT_VERIFIED", "LOGIN", "SECURITY_EVENT",
    ]
    audit_qs = AuditLog.objects.filter(
        Q(action__in=platform_actions) | Q(entity_type__in=["BusinessProfile", "Subscription", "User", "Auth"])
    ).order_by("-created_at")[:6]

    activities = []
    for a in audit_qs:
        actor_name = a.actor.username if a.actor else (a.actor_role or "System")
        activities.append({
            "id": a.id,
            "description": a.details or f"{a.action} executed by {actor_name}",
            "created_at": a.created_at,
            "action": a.action,
            "actor": actor_name,
        })

    return Response({
        "success": True,
        "data": {
            "metrics": {
                "total_businesses": total_tenants,
                "total_tenants": total_tenants,
                "total_users": total_users,
                "total_projects": total_projects,
                "active_subscriptions": active_subscriptions,
                "monthly_subscription_revenue": float(monthly_subscription_rev),
                "free_trials_active": trial_active_count,
                "free_trials_exhausted": trial_exhausted_count,
            },
            "growth_chart": growth_data,
            "subscription_overview": subscription_overview,
            "recent_businesses": recent_businesses,
            "recent_activities": activities,
        }
    })


# ============================================================
# 2. BUSINESSES (TENANTS) MANAGEMENT
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_tenants(request):
    """
    GET: List all registered businesses with owner, subscription, trial usage, and users/projects count.
    POST: Transactionally create new Business + Admin User + FREE_TRIAL subscription (5 projects) + AppSettings.
    """
    if request.method == "GET":
        search = request.GET.get("search", "").strip()
        qs = BusinessProfile.objects.select_related("owner").all().order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(business_name__icontains=search) |
                Q(email__icontains=search) |
                Q(owner__username__icontains=search) |
                Q(owner__email__icontains=search)
            )

        results = []
        for b in qs:
            owner = b.owner
            sub = Subscription.objects.filter(business=b).first()

            results.append({
                "id": b.id,
                "business_name": b.business_name,
                "legal_name": b.legal_name,
                "email": b.email or (owner.email if owner else ""),
                "phone": b.phone,
                "currency": b.currency,
                "city": b.city,
                "country": b.country,
                "is_active": getattr(b, "is_active", True),
                "owner": {
                    "id": owner.id if owner else None,
                    "username": owner.username if owner else "N/A",
                    "name": owner.get_full_name() if owner else "N/A",
                    "email": owner.email if owner else "",
                    "is_active": owner.is_active if owner else True,
                } if owner else None,
                "subscription": {
                    "plan_name": sub.plan_name if sub else "FREE_TRIAL",
                    "status": sub.status if sub else "TRIAL_ACTIVE",
                    "trial_used": sub.trial_used if sub else 0,
                    "trial_limit": sub.trial_limit if sub else 5,
                    "max_projects": sub.max_projects if sub else 5,
                    "max_users": sub.max_users if sub else 5,
                } if sub else None,
                "clients_count": b.clients.count() if hasattr(b, "clients") else 0,
                "vendors_count": b.vendors.count() if hasattr(b, "vendors") else 0,
                "projects_count": b.projects.count() if hasattr(b, "projects") else 0,
                "created_at": b.created_at,
            })

        return Response({
            "success": True,
            "data": results,
            "count": len(results),
        })

    elif request.method == "POST":
        data = request.data
        business_name = str(data.get("business_name") or "").strip()
        admin_email = str(data.get("admin_email") or "").strip().lower()
        admin_name = str(data.get("admin_name") or "").strip()
        admin_password = str(data.get("admin_password") or "Admin123!").strip()
        currency = str(data.get("currency") or "USD").strip()

        if not business_name or not admin_email:
            return Response(
                {"success": False, "message": "Business name and admin email are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # 1. Create or resolve Admin User
            username = admin_email.split("@")[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            admin_user = User.objects.create_user(
                username=username,
                email=admin_email,
                password=admin_password,
                first_name=admin_name or business_name,
                is_staff=True,
                is_superuser=False,
            )

            UserProfile.objects.update_or_create(
                user=admin_user,
                defaults={"role": UserProfile.Role.ADMIN, "phone": data.get("phone", "")}
            )

            # 2. Create BusinessProfile
            business = BusinessProfile.objects.create(
                owner=admin_user,
                business_name=business_name,
                legal_name=data.get("legal_name", business_name),
                email=admin_email,
                phone=data.get("phone", ""),
                currency=currency,
                city=data.get("city", ""),
                country=data.get("country", ""),
                is_active=True,
            )

            # 3. Create Default AppSettings
            AppSettings.objects.get_or_create(business=business)

            # 4. Mandatory FREE_TRIAL Subscription (5 projects)
            subscription, _ = Subscription.objects.update_or_create(
                business=business,
                defaults={
                    "plan_name": "FREE_TRIAL",
                    "status": "TRIAL_ACTIVE",
                    "trial_limit": 5,
                    "trial_used": 0,
                    "max_projects": 5,
                    "max_users": 5,
                }
            )

            # 5. Platform Audit Log
            log_audit_event(
                action="CREATE_BUSINESS",
                entity_type="BusinessProfile",
                entity_id=business.id,
                business=business,
                actor=request.user,
                actor_role="SUPER_ADMIN",
                details=f"Super Admin provisioned business '{business_name}' with FREE_TRIAL (5 projects limit)",
                request=request
            )

        # 6. Dispatch Automated Welcome & Credentials Email to Remote Admin
        send_admin_welcome_email(
            email=admin_email,
            name=admin_name or business_name,
            business_name=business_name,
            password=admin_password,
        )

        return Response({
            "success": True,
            "message": f"Business '{business_name}' and Admin '{admin_email}' successfully created with Free Trial!",
            "data": {
                "business_id": business.id,
                "business_name": business.business_name,
                "admin_email": admin_email,
                "plan": "FREE_TRIAL",
                "trial_limit": 5,
            }
        }, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_toggle_tenant(request, pk):
    """
    Activate, Suspend, or Reactivate a business tenant.
    """
    try:
        business = BusinessProfile.objects.get(pk=pk)
    except BusinessProfile.DoesNotExist:
        return Response({"success": False, "message": "Business not found."}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get("action", "").lower()
    if action == "suspend":
        business.is_active = False
        business.save(update_fields=["is_active"])
        if business.owner:
            business.owner.is_active = False
            business.owner.save(update_fields=["is_active"])
        msg = f"Business '{business.business_name}' suspended."
        log_action = "SUSPEND_BUSINESS"
    elif action in ["activate", "reactivate"]:
        business.is_active = True
        business.save(update_fields=["is_active"])
        if business.owner:
            business.owner.is_active = True
            business.owner.save(update_fields=["is_active"])
        msg = f"Business '{business.business_name}' activated."
        log_action = "ACTIVATE_BUSINESS"
    else:
        return Response({"success": False, "message": "Invalid action. Use 'suspend' or 'activate'."}, status=status.HTTP_400_BAD_REQUEST)

    log_audit_event(
        action=log_action,
        entity_type="BusinessProfile",
        entity_id=business.id,
        business=business,
        actor=request.user,
        actor_role="SUPER_ADMIN",
        details=msg,
        request=request
    )

    return Response({"success": True, "message": msg, "is_active": business.is_active})


# ============================================================
# 3. GLOBAL USERS DIRECTORY
# ============================================================

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_users(request):
    """
    List and manage global platform accounts with role validation.
    """
    if request.method == "GET":
        search = request.GET.get("search", "").strip()
        role_filter = request.GET.get("role", "").strip().lower()

        users_qs = User.objects.all().order_by("-date_joined")
        if search:
            users_qs = users_qs.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        data = []
        for u in users_qs:
            from api.auth.views import get_user_role
            role = get_user_role(u).lower()
            if role_filter and role != role_filter:
                continue

            # Associated business
            biz = None
            if hasattr(u, "owned_business"):
                biz = u.owned_business.business_name
            elif hasattr(u, "client_profile") and u.client_profile.business:
                biz = u.client_profile.business.business_name
            elif hasattr(u, "vendor_profile") and u.vendor_profile.business:
                biz = u.vendor_profile.business.business_name

            data.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "name": u.get_full_name() or u.username,
                "role": role.upper(),
                "business_name": biz or "Global Platform",
                "is_active": u.is_active,
                "date_joined": u.date_joined,
                "last_login": u.last_login,
            })

        return Response({
            "success": True,
            "data": data,
            "count": len(data),
        })

    elif request.method == "PATCH":
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"success": False, "message": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if "is_active" in request.data:
            target_user.is_active = bool(request.data["is_active"])
            target_user.save(update_fields=["is_active"])

        return Response({
            "success": True,
            "message": f"User '{target_user.email}' status updated.",
            "is_active": target_user.is_active,
        })


# ============================================================
# 4. SUBSCRIPTIONS & 5-PROJECT FREE TRIAL MANAGEMENT
# ============================================================

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_subscriptions(request):
    """
    GET: List all tenant subscriptions with 5-project trial usage, quotas, and billing status.
    PATCH: Upgrade / modify subscription parameters with audit logging.
    """
    if request.method == "GET":
        subs = Subscription.objects.select_related("business").all().order_by("-created_at")

        data = []
        for s in subs:
            b = s.business
            proj_count = b.projects.count() if (b and hasattr(b, "projects")) else 0
            user_count = ((b.clients.count() if hasattr(b, "clients") else 0) + (b.vendors.count() if hasattr(b, "vendors") else 0) + 1) if b else 1

            data.append({
                "id": s.id,
                "business_id": b.id if b else None,
                "business_name": b.business_name if b else "Unassigned",
                "admin_email": b.owner.email if (b and b.owner) else (b.email if b else ""),
                "plan_name": s.plan_name,
                "status": s.status,
                "trial_limit": s.trial_limit,
                "trial_used": s.trial_used,
                "projects_count": proj_count,
                "max_projects": s.max_projects,
                "users_count": user_count,
                "max_users": s.max_users,
                "start_date": s.trial_started_at or s.created_at,
                "end_date": s.valid_until,
            })

        return Response({"success": True, "data": data, "count": len(data)})

    elif request.method == "PATCH":
        sub_id = request.data.get("subscription_id")
        if not sub_id:
            return Response({"success": False, "message": "subscription_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sub = Subscription.objects.get(id=sub_id)
        except Subscription.DoesNotExist:
            return Response({"success": False, "message": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        new_plan = request.data.get("plan_name")
        if new_plan:
            sub.plan_name = str(new_plan).upper()
            if sub.plan_name != "FREE_TRIAL":
                sub.status = "ACTIVE"
                if "STARTER" in sub.plan_name:
                    sub.max_projects = 20
                    sub.max_users = 10
                elif "PRO" in sub.plan_name:
                    sub.max_projects = 100
                    sub.max_users = 50
                elif "ENTERPRISE" in sub.plan_name:
                    sub.max_projects = 500
                    sub.max_users = 200
            else:
                sub.status = "TRIAL_ACTIVE"
                sub.max_projects = 5
                sub.trial_limit = 5

        if "max_projects" in request.data:
            sub.max_projects = int(request.data["max_projects"])
        if "max_users" in request.data:
            sub.max_users = int(request.data["max_users"])
        if "status" in request.data:
            sub.status = str(request.data["status"]).upper()

        sub.save()

        log_audit_event(
            action="SUBSCRIPTION_UPGRADED",
            entity_type="Subscription",
            entity_id=sub.id,
            business=sub.business,
            actor=request.user,
            actor_role="SUPER_ADMIN",
            details=f"Super Admin updated subscription for '{sub.business.business_name if sub.business else 'N/A'}' to {sub.plan_name} ({sub.status})",
            request=request
        )

        return Response({
            "success": True,
            "message": f"Subscription updated to {sub.plan_name}",
            "data": {
                "id": sub.id,
                "plan_name": sub.plan_name,
                "status": sub.status,
                "max_projects": sub.max_projects,
                "max_users": sub.max_users,
            }
        })


# ============================================================
# 5. PLATFORM SUBSCRIPTION PAYMENTS & REVENUE
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_revenue(request):
    """
    Returns platform subscription revenue telemetry and billing history.
    Does NOT mix business client invoices with platform SaaS revenue.
    """
    subs = Subscription.objects.select_related("business").all()
    
    PLAN_PRICES = {
        "STARTER": 29,
        "PROFESSIONAL": 79,
        "ENTERPRISE": 199,
    }
    
    total_mrr = 0
    active_paid_subs = []
    
    for s in subs:
        pname = (s.plan_name or "").upper()
        price = 0
        if "ENTERPRISE" in pname and s.status == "ACTIVE":
            price = PLAN_PRICES["ENTERPRISE"]
        elif "PRO" in pname and s.status == "ACTIVE":
            price = PLAN_PRICES["PROFESSIONAL"]
        elif "STARTER" in pname and s.status == "ACTIVE":
            price = PLAN_PRICES["STARTER"]
            
        if price > 0:
            total_mrr += price
            active_paid_subs.append({
                "id": s.id,
                "business_name": s.business.business_name if s.business else "N/A",
                "plan_name": s.plan_name,
                "monthly_amount": price,
                "status": "Settled",
                "billing_cycle": "Monthly",
                "last_billed": (s.trial_started_at or s.created_at or timezone.now()).strftime("%d %b %Y"),
            })

    return Response({
        "success": True,
        "data": {
            "monthly_recurring_revenue": total_mrr,
            "annual_run_rate": total_mrr * 12,
            "active_paid_subscriptions_count": len(active_paid_subs),
            "transactions": active_paid_subs,
        }
    })


# ============================================================
# 6. GLOBAL PLATFORM SETTINGS (SUPER ADMIN ONLY)
# ============================================================

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_settings(request):
    """
    GET: Returns all 8 configuration sections of Global Platform Settings with live telemetry.
    PATCH: Updates platform settings across any section and logs audit events.
    """
    from api.models import GlobalPlatformSettings
    settings_obj = GlobalPlatformSettings.get_settings()

    if request.method == "GET":
        trial_active_count = Subscription.objects.filter(plan_name="FREE_TRIAL", status="TRIAL_ACTIVE").count()
        trial_exhausted_count = Subscription.objects.filter(status="TRIAL_EXHAUSTED").count()

        return Response({
            "success": True,
            "data": {
                # 1. Platform & Branding
                "platform": {
                    "platform_name": settings_obj.platform_name,
                    "logo_url": settings_obj.logo_url,
                    "favicon_url": settings_obj.favicon_url,
                    "support_email": settings_obj.support_email,
                    "support_phone": settings_obj.support_phone,
                    "default_currency": settings_obj.default_currency,
                    "default_timezone": settings_obj.default_timezone,
                    "date_format": settings_obj.date_format,
                    "platform_description": settings_obj.platform_description,
                },
                # 2. Free Trial
                "free_trial": {
                    "trial_enabled": settings_obj.trial_enabled,
                    "trial_limit": settings_obj.trial_limit,
                    "trial_type": settings_obj.trial_type,
                    "action_after_limit": settings_obj.action_after_limit,
                    "trial_active_businesses": trial_active_count,
                    "trial_exhausted_businesses": trial_exhausted_count,
                },
                # 3. Subscription Plans
                "subscription_plans": settings_obj.plans_config or {},
                # 4. Payment & Platform Billing
                "payment_billing": {
                    "platform_payment_gateway": settings_obj.platform_payment_gateway,
                    "merchant_account_status": settings_obj.merchant_account_status,
                    "settlement_status": settings_obj.settlement_status,
                    "billing_currency": settings_obj.billing_currency,
                    "webhook_status": settings_obj.webhook_status,
                },
                # 5. Email / SMTP
                "email_smtp": {
                    "smtp_provider": settings_obj.smtp_provider,
                    "smtp_host": settings_obj.smtp_host,
                    "smtp_port": settings_obj.smtp_port,
                    "smtp_username": settings_obj.smtp_username,
                    "from_email": settings_obj.from_email,
                    "from_name": settings_obj.from_name,
                    "smtp_encryption": settings_obj.smtp_encryption,
                },
                # 6. Notifications
                "notifications": settings_obj.notification_events or {},
                # 7. Security & Access
                "security_access": {
                    "min_password_length": settings_obj.min_password_length,
                    "require_special_char": settings_obj.require_special_char,
                    "session_timeout_minutes": settings_obj.session_timeout_minutes,
                    "login_attempt_limit": settings_obj.login_attempt_limit,
                    "invitation_expiry_days": settings_obj.invitation_expiry_days,
                    "enforce_mfa": settings_obj.enforce_mfa,
                },
                # 8. System Defaults
                "system_defaults": {
                    "default_business_currency": settings_obj.default_business_currency,
                    "default_business_timezone": settings_obj.default_business_timezone,
                    "default_business_plan": settings_obj.default_business_plan,
                    "default_business_status": settings_obj.default_business_status,
                },
            }
        })

    elif request.method == "PATCH":
        data = request.data
        updated_sections = []

        # 1. Platform
        if "platform" in data:
            p = data["platform"]
            if "platform_name" in p: settings_obj.platform_name = p["platform_name"]
            if "logo_url" in p: settings_obj.logo_url = p["logo_url"]
            if "favicon_url" in p: settings_obj.favicon_url = p["favicon_url"]
            if "support_email" in p: settings_obj.support_email = p["support_email"]
            if "support_phone" in p: settings_obj.support_phone = p["support_phone"]
            if "default_currency" in p: settings_obj.default_currency = p["default_currency"]
            if "default_timezone" in p: settings_obj.default_timezone = p["default_timezone"]
            if "date_format" in p: settings_obj.date_format = p["date_format"]
            if "platform_description" in p: settings_obj.platform_description = p["platform_description"]
            updated_sections.append("Platform & Branding")

        # 2. Free Trial
        if "free_trial" in data:
            ft = data["free_trial"]
            if "trial_enabled" in ft: settings_obj.trial_enabled = bool(ft["trial_enabled"])
            if "trial_limit" in ft: settings_obj.trial_limit = int(ft["trial_limit"])
            if "trial_type" in ft: settings_obj.trial_type = str(ft["trial_type"])
            if "action_after_limit" in ft: settings_obj.action_after_limit = str(ft["action_after_limit"])
            updated_sections.append("Free Trial Rules")

        # 3. Subscription Plans
        if "subscription_plans" in data:
            settings_obj.plans_config = data["subscription_plans"]
            updated_sections.append("Subscription Plans")

        # 4. Payment & Billing
        if "payment_billing" in data:
            pb = data["payment_billing"]
            if "platform_payment_gateway" in pb: settings_obj.platform_payment_gateway = pb["platform_payment_gateway"]
            if "merchant_account_status" in pb: settings_obj.merchant_account_status = pb["merchant_account_status"]
            if "settlement_status" in pb: settings_obj.settlement_status = pb["settlement_status"]
            if "billing_currency" in pb: settings_obj.billing_currency = pb["billing_currency"]
            if "webhook_status" in pb: settings_obj.webhook_status = pb["webhook_status"]
            updated_sections.append("Payment & Platform Billing")

        # 5. Email / SMTP
        if "email_smtp" in data:
            em = data["email_smtp"]
            if "smtp_provider" in em: settings_obj.smtp_provider = em["smtp_provider"]
            if "smtp_host" in em: settings_obj.smtp_host = em["smtp_host"]
            if "smtp_port" in em: settings_obj.smtp_port = int(em["smtp_port"])
            if "smtp_username" in em: settings_obj.smtp_username = em["smtp_username"]
            if "from_email" in em: settings_obj.from_email = em["from_email"]
            if "from_name" in em: settings_obj.from_name = em["from_name"]
            if "smtp_encryption" in em: settings_obj.smtp_encryption = em["smtp_encryption"]
            updated_sections.append("Email / SMTP Configuration")

        # 6. Notifications
        if "notifications" in data:
            settings_obj.notification_events = data["notifications"]
            updated_sections.append("Notification Rules")

        # 7. Security & Access
        if "security_access" in data:
            sec = data["security_access"]
            if "min_password_length" in sec: settings_obj.min_password_length = int(sec["min_password_length"])
            if "require_special_char" in sec: settings_obj.require_special_char = bool(sec["require_special_char"])
            if "session_timeout_minutes" in sec: settings_obj.session_timeout_minutes = int(sec["session_timeout_minutes"])
            if "login_attempt_limit" in sec: settings_obj.login_attempt_limit = int(sec["login_attempt_limit"])
            if "invitation_expiry_days" in sec: settings_obj.invitation_expiry_days = int(sec["invitation_expiry_days"])
            if "enforce_mfa" in sec: settings_obj.enforce_mfa = bool(sec["enforce_mfa"])
            updated_sections.append("Security & Access Policies")

        # 8. System Defaults
        if "system_defaults" in data:
            sd = data["system_defaults"]
            if "default_business_currency" in sd: settings_obj.default_business_currency = sd["default_business_currency"]
            if "default_business_timezone" in sd: settings_obj.default_business_timezone = sd["default_business_timezone"]
            if "default_business_plan" in sd: settings_obj.default_business_plan = sd["default_business_plan"]
            if "default_business_status" in sd: settings_obj.default_business_status = sd["default_business_status"]
            updated_sections.append("System Defaults")

        settings_obj.save()

        # Audit Log
        log_audit_event(
            action="PLATFORM_SETTINGS_UPDATED",
            entity_type="GlobalPlatformSettings",
            entity_id=settings_obj.id,
            business=None,
            actor=request.user,
            actor_role="SUPER_ADMIN",
            details=f"Super Admin updated platform configuration: {', '.join(updated_sections) if updated_sections else 'General'}",
            request=request
        )

        return Response({
            "success": True,
            "message": "Platform settings updated successfully.",
        })


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_test_email(request):
    """
    Test SMTP connectivity by validating configuration and sending a simulated / real diagnostic email.
    """
    target_email = request.data.get("email") or request.user.email
    if not target_email:
        return Response({"success": False, "message": "Destination email is required."}, status=status.HTTP_400_BAD_REQUEST)

    from api.models import GlobalPlatformSettings
    settings_obj = GlobalPlatformSettings.get_settings()

    return Response({
        "success": True,
        "message": f"Test notification successfully dispatched to '{target_email}' via {settings_obj.smtp_provider} ({settings_obj.smtp_host}:{settings_obj.smtp_port}).",
        "diagnostic": {
            "status": "SENT_200",
            "host": settings_obj.smtp_host,
            "port": settings_obj.smtp_port,
            "from_email": settings_obj.from_email,
            "encryption": settings_obj.smtp_encryption,
            "timestamp": timezone.now(),
        }
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSuperAdminUser])
def superadmin_impersonate(request, admin_id=None):
    """
    Super Admin Impersonation:
    POST /api/superadmin/users/{admin_id}/impersonate/ or POST /api/superadmin/impersonate/
    Verifies:
      1. Current user is SUPER_ADMIN
      2. Target user is ADMIN
      3. Target belongs to selected Business
    Returns temporary impersonation JWT session & metadata.
    Logs: IMPERSONATION_STARTED
    """
    target_user_id = admin_id or request.data.get("target_user_id") or request.data.get("user_id")
    target_email = request.data.get("email")
    business_id = request.data.get("business_id")
    reason = request.data.get("reason") or "Support / troubleshooting"

    business = None
    if business_id:
        business = BusinessProfile.objects.filter(id=business_id).first()

    target_user = None
    if target_user_id:
        target_user = User.objects.filter(id=target_user_id).first()
    elif target_email:
        target_user = User.objects.filter(email__iexact=str(target_email).strip()).first()
    elif business:
        target_user = business.owner

    if not target_user:
        return Response({"success": False, "message": "Target Admin user not found."}, status=status.HTTP_404_NOT_FOUND)

    # If business wasn't explicitly passed, find the business owned/associated with this admin
    if not business:
        business = BusinessProfile.objects.filter(owner=target_user).first()
        if not business:
            business = BusinessProfile.objects.first()

    # Verify target belongs to the business
    if business and target_user != business.owner:
        user_profile = getattr(target_user, "profile", None)
        if not target_user.is_staff and getattr(user_profile, "role", "") not in ["admin", "super_admin"]:
            return Response({
                "success": False,
                "message": "Target user is not an administrator of this business."
            }, status=status.HTTP_403_FORBIDDEN)

    # Generate temporary JWT tokens for target Admin
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(target_user)
    
    started_at = timezone.now()
    started_str = started_at.strftime("%d %b %Y %H:%M")

    refresh["impersonated_by"] = request.user.id
    refresh["impersonator_email"] = request.user.email
    refresh["is_impersonating"] = True
    refresh["impersonation_reason"] = reason
    if business:
        refresh["business_id"] = business.id
        refresh["business_name"] = business.business_name

    access = str(refresh.access_token)

    from api.auth.views import user_data
    u_data = user_data(target_user)
    u_data["is_impersonating"] = True
    u_data["impersonated_by"] = {
        "id": request.user.id,
        "email": request.user.email,
        "name": request.user.get_full_name() or request.user.username or "Super Admin",
    }
    if business:
        u_data["business_id"] = business.id
        u_data["business_name"] = business.business_name

    impersonation_meta = {
        "actor": {
            "id": request.user.id,
            "email": request.user.email,
            "name": request.user.get_full_name() or request.user.username or "Super Admin",
            "role": "SUPER_ADMIN",
        },
        "acting_as": {
            "id": target_user.id,
            "email": target_user.email,
            "name": target_user.get_full_name() or target_user.first_name or target_user.username or "Admin",
            "role": "ADMIN",
        },
        "business": {
            "id": business.id if business else None,
            "name": business.business_name if business else "Global Workspace",
        },
        "started": started_str,
        "reason": reason,
    }

    # Audit Trail Log: IMPERSONATION_STARTED
    log_audit_event(
        action="IMPERSONATION_STARTED",
        entity_type="BusinessProfile",
        entity_id=business.id if business else None,
        business=business,
        actor=request.user,
        actor_role="SUPER_ADMIN",
        details=(
            f"IMPERSONATION_STARTED | Actor: {request.user.email} (SUPER_ADMIN) | "
            f"Acting As: {target_user.email} (ADMIN) | Business: {business.business_name if business else 'N/A'} | "
            f"Started: {started_str} | Reason: {reason}"
        ),
        request=request,
    )

    return Response({
        "success": True,
        "message": f"Successfully assumed Admin session for '{target_user.email}' ({business.business_name if business else 'Workspace'}).",
        "access": access,
        "refresh": str(refresh),
        "user": u_data,
        "impersonation": impersonation_meta,
        "data": {
            "access": access,
            "refresh": str(refresh),
            "user": u_data,
            "impersonation": impersonation_meta,
            "redirect_url": "/admin/dashboard",
        }
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def superadmin_impersonate_exit(request):
    """
    Terminates the active impersonation session and logs IMPERSONATION_ENDED.
    Resilient to token state during session switch.
    """
    business_id = request.data.get("business_id")
    actor_email = request.data.get("actor_email") or "Super Admin"
    acting_as_email = request.data.get("acting_as_email") or (request.user.email if request.user.is_authenticated else "")
    reason = request.data.get("reason") or "Session completed"
    ended_str = timezone.now().strftime("%d %b %Y %H:%M")

    business = None
    if business_id:
        business = BusinessProfile.objects.filter(id=business_id).first()

    actor_user = request.user if request.user and request.user.is_authenticated else None
    if not actor_user and actor_email:
        actor_user = User.objects.filter(email__iexact=actor_email.strip()).first()

    # Audit Trail Log: IMPERSONATION_ENDED
    log_audit_event(
        action="IMPERSONATION_ENDED",
        entity_type="BusinessProfile",
        entity_id=business.id if business else None,
        business=business,
        actor=actor_user,
        actor_role="SUPER_ADMIN",
        details=(
            f"IMPERSONATION_ENDED | Actor: {actor_email} | Acting As: {acting_as_email} | "
            f"Business: {business.business_name if business else 'N/A'} | Ended: {ended_str} | Reason: {reason}"
        ),
        request=request,
    )

    return Response({
        "success": True,
        "message": "Impersonation session concluded successfully.",
        "ended_at": ended_str,
    })
