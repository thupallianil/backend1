import logging
from .models import AuditLog, Notification

logger = logging.getLogger(__name__)


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_event(
    action,
    entity_type,
    entity_id="",
    business=None,
    actor=None,
    actor_role="",
    details="",
    request=None,
):
    """
    Records an immutable audit event for compliance, tracing, and superadmin monitoring.
    """
    try:
        ip = get_client_ip(request) if request else None
        role = actor_role
        if not role and actor:
            if getattr(actor, "is_superuser", False) or getattr(getattr(actor, "profile", None), "role", "") == "super_admin":
                role = "SUPER_ADMIN"
            elif getattr(actor, "is_staff", False) or getattr(getattr(actor, "profile", None), "role", "") == "admin":
                role = "ADMIN"
            elif getattr(getattr(actor, "profile", None), "role", "") == "vendor":
                role = "VENDOR"
            else:
                role = "CLIENT"

        return AuditLog.objects.create(
            business=business,
            actor=actor,
            actor_role=role or "SYSTEM",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=str(details),
            ip_address=ip,
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        return None


def send_system_notification(
    user,
    title,
    message,
    business=None,
    notif_type="system",
    link="",
):
    """
    Dispatches a dynamic persistent notification to a user.
    """
    if not user:
        return None
    try:
        return Notification.objects.create(
            user=user,
            business=business,
            title=title,
            message=message,
            type=notif_type,
            link=link,
        )
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return None
