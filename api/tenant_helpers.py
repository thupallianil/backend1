from api.models import BusinessProfile, Client, Vendor, UserProfile


def resolve_user_context(user):
    """
    Determines user's role and associated business tenant.
    Returns: (role: str, business: BusinessProfile|None, entity: Client|Vendor|None)
    """
    if not user or not user.is_authenticated:
        return "ANONYMOUS", None, None

    # Check superuser / super_admin role
    if user.is_superuser or getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.SUPER_ADMIN:
        return "SUPER_ADMIN", None, None

    # Check Admin (Business Owner)
    biz = BusinessProfile.objects.filter(owner=user).first()
    if biz or user.is_staff or getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.ADMIN:
        if not biz:
            biz = BusinessProfile.objects.first()
        return "ADMIN", biz, None

    # Check Vendor
    vendor = Vendor.objects.filter(user=user).first()
    if not vendor and hasattr(user, "profile") and user.profile.vendor:
        vendor = user.profile.vendor
    if not vendor:
        vendor = Vendor.objects.filter(email__iexact=user.email).first()

    if vendor or getattr(getattr(user, "profile", None), "role", None) == UserProfile.Role.VENDOR:
        biz = vendor.business if vendor else None
        return "VENDOR", biz, vendor

    # Check Client
    client = Client.objects.filter(user=user).first()
    if not client and hasattr(user, "profile") and user.profile.client:
        client = user.profile.client
    if not client:
        client = Client.objects.filter(email__iexact=user.email).first()

    biz = client.business if client else None
    return "CLIENT", biz, client


def get_request_business(request, require_active=False):
    """
    Retrieves the business for the current request.
    If superadmin passed ?business_id=X, resolves to that business.
    """
    user = request.user
    if not user or not user.is_authenticated:
        return None

    role, biz, _ = resolve_user_context(user)
    if role == "SUPER_ADMIN":
        biz_id = request.query_params.get("business_id") or request.data.get("business_id")
        if biz_id:
            return BusinessProfile.objects.filter(id=biz_id).first()
        return BusinessProfile.objects.first()

    if biz and require_active and not biz.is_active:
        return None

    return biz
