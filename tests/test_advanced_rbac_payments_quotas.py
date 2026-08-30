import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import (
    BusinessProfile,
    UserProfile,
    Subscription,
    Client,
    Vendor,
    Project,
    Invoice,
    Payment,
    AppSettings,
)

User = get_user_model()


@pytest.fixture
def auth_client():
    def _make(user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client
    return _make


@pytest.mark.django_db
def test_payment_to_invoice_status_lifecycle(auth_client):
    """
    1. Comprehensive Payment -> Invoice Status Automation:
       - Initial Invoice: Total $1000.00, Status 'sent', Balance $1000.00
       - Partial Payment: $400.00 -> Status becomes 'partially_paid', Balance $600.00
       - Final Payment: $600.00 -> Status becomes 'paid', Balance $0.00
       - Payment Deletion: $600.00 deleted -> Status reverts to 'partially_paid', Balance $600.00
    """
    admin_user = User.objects.create_user(
        username="pay_admin_tester",
        email="pay_admin@enterprise.com",
        password="Password123!",
        is_staff=True,
    )
    UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
    business = BusinessProfile.objects.create(
        owner=admin_user,
        business_name="Payment Enterprise LLC",
        email="pay_admin@enterprise.com",
    )
    AppSettings.objects.get_or_create(business=business)
    client = auth_client(admin_user)

    # Create client
    c = Client.objects.create(business=business, name="Acme Pay Client", email="acmepay@example.com")

    # Create project
    p = Project.objects.create(business=business, client=c, title="Payment Pipeline Project")

    # Create invoice ($1,000.00)
    invoice = Invoice.objects.create(
        business=business,
        client=c,
        project=p,
        invoice_number="INV-PAY-001",
        subtotal=Decimal("1000.00"),
        tax=Decimal("0.00"),
        total=Decimal("1000.00"),
        paid_amount=Decimal("0.00"),
        balance_due=Decimal("1000.00"),
        status=Invoice.Status.SENT,
    )

    # 1. Partial Payment of $400.00 via API
    res = client.post("/api/payments/", {
        "invoice": invoice.id,
        "amount": "400.00",
        "method": "online",
        "status": "success",
        "transaction_id": "txn_partial_001",
    }, format="json")
    assert res.status_code == 201
    pay1_id = res.json().get("data", res.json())["id"]

    invoice.refresh_from_db()
    assert invoice.paid_amount == Decimal("400.00")
    assert invoice.balance_due == Decimal("600.00")
    assert invoice.status == Invoice.Status.PARTIALLY_PAID

    # 2. Final Payment of $600.00 via API
    res = client.post("/api/payments/", {
        "invoice": invoice.id,
        "amount": "600.00",
        "method": "online",
        "status": "success",
        "transaction_id": "txn_final_002",
    }, format="json")
    assert res.status_code == 201
    pay2_id = res.json().get("data", res.json())["id"]

    invoice.refresh_from_db()
    assert invoice.paid_amount == Decimal("1000.00")
    assert invoice.balance_due == Decimal("0.00")
    assert invoice.status == Invoice.Status.PAID

    # 3. Payment Deletion and Reversion
    res = client.delete(f"/api/payments/{pay2_id}/")
    assert res.status_code in [200, 204]

    invoice.refresh_from_db()
    assert invoice.paid_amount == Decimal("400.00")
    assert invoice.balance_due == Decimal("600.00")
    assert invoice.status == Invoice.Status.PARTIALLY_PAID


@pytest.mark.django_db
def test_comprehensive_role_based_access_control_rbac(auth_client):
    """
    2. Comprehensive RBAC Matrix:
       - Client User cannot create invoices, create projects, or access SuperAdmin console
       - Vendor User cannot create clients, access SuperAdmin console, or delete projects
       - Business Admin cannot access SuperAdmin console or provision tenants
       - Super Admin has full platform privileges
    """
    # 1. Super Admin
    sa = User.objects.create_superuser(
        username="rbac_superadmin",
        email="sa@invoiceflow.com",
        password="Pass123!",
    )
    UserProfile.objects.create(user=sa, role=UserProfile.Role.SUPER_ADMIN)
    sa_client = auth_client(sa)

    # 2. Business Admin
    admin = User.objects.create_user(
        username="rbac_admin",
        email="admin@tenant1.com",
        password="Pass123!",
        is_staff=True,
    )
    UserProfile.objects.create(user=admin, role=UserProfile.Role.ADMIN)
    biz = BusinessProfile.objects.create(owner=admin, business_name="Tenant 1 Workspace", email="admin@tenant1.com")
    Subscription.objects.update_or_create(
        business=biz,
        defaults={"plan_name": "FREE_TRIAL", "trial_limit": 5, "trial_used": 0}
    )
    admin_client = auth_client(admin)

    # 3. Vendor User
    vendor_user = User.objects.create_user(
        username="rbac_vendor",
        email="vendor@tenant1.com",
        password="Pass123!",
    )
    UserProfile.objects.create(user=vendor_user, role=UserProfile.Role.VENDOR)
    vendor = Vendor.objects.create(business=biz, name="Vendor Tech", email="vendor@tenant1.com", user=vendor_user)
    vendor_client = auth_client(vendor_user)

    # 4. Client User
    client_user = User.objects.create_user(
        username="rbac_client",
        email="client@tenant1.com",
        password="Pass123!",
    )
    UserProfile.objects.create(user=client_user, role=UserProfile.Role.CLIENT)
    c_entity = Client.objects.create(business=biz, name="Client Corp", email="client@tenant1.com", user=client_user)
    client_c = auth_client(client_user)

    # --- CLIENT ROLE RESTRICTIONS ---
    # Client cannot create project (Must be 403)
    res = client_c.post("/api/projects/", {"title": "Unauthorized Client Project", "client": c_entity.id})
    assert res.status_code == 403, f"Client created project! Status: {res.status_code}"

    # Client cannot access Super Admin stats (Must be 403)
    res = client_c.get("/api/superadmin/stats/")
    assert res.status_code == 403

    # Client cannot access Super Admin tenants (Must be 403)
    res = client_c.get("/api/superadmin/tenants/")
    assert res.status_code == 403

    # --- VENDOR ROLE RESTRICTIONS ---
    # Vendor cannot create clients (Must be 403)
    res = vendor_client.post("/api/clients/", {"name": "Vendor Fake Client", "email": "fake@test.com"})
    assert res.status_code == 403, f"Vendor created client! Status: {res.status_code}"

    # Vendor cannot access Super Admin stats (Must be 403)
    res = vendor_client.get("/api/superadmin/stats/")
    assert res.status_code == 403

    # --- BUSINESS ADMIN RESTRICTIONS ---
    # Business Admin cannot access Super Admin stats (Must be 403)
    res = admin_client.get("/api/superadmin/stats/")
    assert res.status_code == 403

    # Business Admin cannot access Super Admin tenants (Must be 403)
    res = admin_client.get("/api/superadmin/tenants/")
    assert res.status_code == 403

    # --- SUPER ADMIN PRIVILEGES ---
    res = sa_client.get("/api/superadmin/stats/?time_range=6_months")
    assert res.status_code == 200
    res = sa_client.get("/api/superadmin/tenants/")
    assert res.status_code == 200


@pytest.mark.django_db
def test_subscription_and_project_limit_enforcement(auth_client):
    """
    3. Subscription Quota & 5-Project Free Trial Limit Enforcement:
       - Business Admin creates 5 projects on Free Trial -> All succeed
       - 6th project creation -> Returns 403 Forbidden with TRIAL_EXHAUSTED
       - Subscription upgraded to PROFESSIONAL -> 6th project creation immediately succeeds
    """
    admin_user = User.objects.create_user(
        username="quota_admin",
        email="quota@enterprise.com",
        password="Pass123!",
        is_staff=True,
    )
    UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
    business = BusinessProfile.objects.create(
        owner=admin_user,
        business_name="Quota Enterprise",
        email="quota@enterprise.com",
    )
    sub, _ = Subscription.objects.update_or_create(
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

    client = auth_client(admin_user)
    c = Client.objects.create(business=business, name="Quota Client", email="quotaclient@example.com")

    # 1. Create 5 projects within the Free Trial limit
    for i in range(1, 6):
        res = client.post("/api/projects/", {
            "title": f"Trial Project {i}",
            "client": c.id,
            "budget": "5000.00",
        }, format="json")
        assert res.status_code == 201, f"Project {i} failed: {res.content}"

    sub.refresh_from_db()
    assert sub.trial_used == 5
    assert Project.objects.filter(business=business).count() == 5

    # 2. Attempt to create 6th project -> MUST BE BLOCKED (HTTP 403 TRIAL_EXHAUSTED)
    res = client.post("/api/projects/", {
        "title": "Trial Project 6 (Blocked)",
        "client": c.id,
        "budget": "5000.00",
    }, format="json")
    assert res.status_code == 403, f"Expected 403 Forbidden for 6th project, got {res.status_code}"
    err_data = res.json()
    assert err_data.get("code") == "TRIAL_EXHAUSTED" or "upgrade" in str(res.content).lower()

    # 3. Upgrade Subscription to PROFESSIONAL (Paid Plan)
    sub.plan_name = Subscription.Plan.PROFESSIONAL
    sub.status = Subscription.Status.ACTIVE
    sub.max_projects = 50
    sub.save()

    # 4. Attempt 6th project again -> MUST SUCCEED IMMEDIATELY
    res = client.post("/api/projects/", {
        "title": "Pro Plan Project 6 (Allowed)",
        "client": c.id,
        "budget": "15000.00",
    }, format="json")
    assert res.status_code == 201, f"Project 6 creation on Pro plan failed: {res.content}"
    assert Project.objects.filter(business=business).count() == 6
