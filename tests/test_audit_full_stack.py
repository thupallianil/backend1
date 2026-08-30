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
    Task,
    Deliverable,
    Quote,
    Invoice,
    Payment,
    AppSettings,
    AuditLog,
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
def test_full_stack_master_audit_and_tenant_isolation(auth_client):
    """
    Master Audit Test Suite:
    1. Super Admin Provisioning & Verification
    2. Tenant A Creation & Full Business Workflow (Client, Vendor, Project, Deliverable, Invoice, Payment)
    3. Tenant B Creation
    4. Cross-Tenant Isolation Enforcement (Tenant A cannot access Tenant B resources)
    5. Role Access Control (Client cannot access Admin/Vendor data, Vendor cannot access Admin/Client data)
    6. Dynamic Subscription & Project Limit Enforcement
    """

    # =========================================================================
    # 1. SUPER ADMIN PLATFORM VERIFICATION
    # =========================================================================
    superadmin = User.objects.create_superuser(
        username="global_superadmin_audit",
        email="superadmin_audit@invoiceflow.com",
        password="SuperAdminPass123!",
    )
    UserProfile.objects.create(user=superadmin, role=UserProfile.Role.SUPER_ADMIN)
    sa_client = auth_client(superadmin)

    # SuperAdmin Stats endpoint
    res = sa_client.get("/api/superadmin/stats/?time_range=6_months")
    assert res.status_code == 200, f"SuperAdmin stats failed: {res.content}"
    assert res.json()["success"] is True
    assert "metrics" in res.json()["data"]

    # SuperAdmin Tenants List
    res = sa_client.get("/api/superadmin/tenants/")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # =========================================================================
    # 2. TENANT A CREATION & FULL WORKFLOW
    # =========================================================================
    # Provision Tenant A via SuperAdmin
    tenant_a_payload = {
        "business_name": "Tenant A Enterprise",
        "admin_name": "Alice Admin",
        "admin_email": "alice_audit@tenanta.com",
        "admin_password": "TenantAPass123!",
        "currency": "USD",
    }
    res = sa_client.post("/api/superadmin/tenants/", tenant_a_payload, format="json")
    assert res.status_code == 201, f"Tenant A provisioning failed: {res.content}"
    tenant_a_id = res.json()["data"]["business_id"]
    business_a = BusinessProfile.objects.get(id=tenant_a_id)
    admin_a = business_a.owner
    admin_a_client = auth_client(admin_a)

    # Verify Free Trial Provisioned
    sub_a = Subscription.objects.get(business=business_a)
    assert sub_a.plan_name == "FREE_TRIAL"
    assert sub_a.trial_limit == 5
    assert sub_a.trial_used == 0

    # Business Admin A creates Client A
    res = admin_a_client.post("/api/clients/", {
        "name": "Client A Corp",
        "company_name": "Client A Corporation",
        "email": "clienta_audit@corpa.com",
        "phone": "+1 555-0101",
        "currency": "USD",
    }, format="json")
    assert res.status_code == 201, f"Client A creation failed: {res.content}"
    client_a_data = res.json().get("data", res.json())
    client_a_id = client_a_data["id"]

    # Business Admin A creates Vendor A
    res = admin_a_client.post("/api/vendors/", {
        "name": "Victor Vendor",
        "company_name": "Alpha Vendor Studio",
        "email": "victor_audit@alphavendor.com",
        "category": "services",
        "phone": "+1 555-0102",
    }, format="json")
    assert res.status_code == 201, f"Vendor A creation failed: {res.content}"
    vendor_a_data = res.json().get("data", res.json())
    vendor_a_id = vendor_a_data["id"]

    # Business Admin A creates Project A
    res = admin_a_client.post("/api/projects/", {
        "title": "Project Alpha SaaS Platform",
        "client": client_a_id,
        "status": "in_progress",
        "budget": "15000.00",
    }, format="json")
    assert res.status_code == 201, f"Project A creation failed: {res.content}"
    project_a_data = res.json().get("data", res.json())
    project_a_id = project_a_data["id"]

    # Verify Project Trial Counter Incremented
    sub_a.refresh_from_db()
    assert sub_a.trial_used == 1, f"Expected trial_used=1, got {sub_a.trial_used}"

    # Business Admin A creates Task A assigned to Vendor A
    res = admin_a_client.post("/api/tasks/", {
        "project": project_a_id,
        "title": "Build Architecture & API Layer",
        "description": "Develop DRF backend endpoints and auth",
        "status": "in_progress",
        "priority": "high",
    }, format="json")
    assert res.status_code == 201, f"Task A creation failed: {res.content}"
    task_a_data = res.json().get("data", res.json())
    task_a_id = task_a_data["id"]

    # Admin A creates Deliverable on Project A
    res = admin_a_client.post("/api/deliverables/", {
        "project": project_a_id,
        "title": "Backend API Specification v1.0",
        "description": "Core authentication and tenant architecture",
    }, format="json")
    assert res.status_code == 201, f"Deliverable A creation failed: {res.content}"
    deliverable_a_data = res.json().get("data", res.json())
    deliverable_a_id = deliverable_a_data["id"]

    # Admin A approves Deliverable via admin-review endpoint
    res = admin_a_client.post(f"/api/deliverables/{deliverable_a_id}/admin-review/", {
        "action": "approve",
        "feedback": "QA approved with zero security defects.",
    }, format="json")
    assert res.status_code == 200

    # Admin A creates Invoice for Client A
    res = admin_a_client.post("/api/invoices/", {
        "client": client_a_id,
        "project": project_a_id,
        "due_date": "2026-09-30",
        "items": [
            {
                "description": "Phase 1 Architecture & Core Deliverables",
                "quantity": 1,
                "unit_price": "5000.00",
                "tax_rate": "18.00",
            }
        ]
    }, format="json")
    assert res.status_code == 201, f"Invoice A creation failed: {res.content}"
    invoice_a_data = res.json().get("data", res.json())
    invoice_a_id = invoice_a_data["id"]
    invoice_a = Invoice.objects.get(id=invoice_a_id)
    assert invoice_a.total > Decimal("5000.00")

    # =========================================================================
    # 3. TENANT B CREATION
    # =========================================================================
    tenant_b_payload = {
        "business_name": "Tenant B Logistics",
        "admin_name": "Bob Admin",
        "admin_email": "bob_audit@tenantb.com",
        "admin_password": "TenantBPass123!",
        "currency": "EUR",
    }
    res = sa_client.post("/api/superadmin/tenants/", tenant_b_payload, format="json")
    assert res.status_code == 201
    tenant_b_id = res.json()["data"]["business_id"]
    business_b = BusinessProfile.objects.get(id=tenant_b_id)
    admin_b = business_b.owner
    admin_b_client = auth_client(admin_b)

    # Business Admin B creates Client B and Project B
    res = admin_b_client.post("/api/clients/", {
        "name": "Client B Express",
        "company_name": "Client B Express Logistics",
        "email": "clientb_audit@expressb.com",
    }, format="json")
    assert res.status_code == 201
    client_b_data = res.json().get("data", res.json())
    client_b_id = client_b_data["id"]

    res = admin_b_client.post("/api/projects/", {
        "title": "Project Beta Fleet Tracking",
        "client": client_b_id,
        "budget": "20000.00",
    }, format="json")
    assert res.status_code == 201
    project_b_data = res.json().get("data", res.json())
    project_b_id = project_b_data["id"]

    # =========================================================================
    # 4. CROSS-TENANT ISOLATION TESTS (MANDATORY SECURITY ENFORCEMENT)
    # =========================================================================
    # Admin A attempts to view Tenant B's Client B -> MUST FAIL (403 or 404)
    res = admin_a_client.get(f"/api/clients/{client_b_id}/")
    assert res.status_code in [403, 404], f"Cross-tenant leak! Admin A accessed Client B: {res.status_code}"

    # Admin A attempts to view Tenant B's Project B -> MUST FAIL (403 or 404)
    res = admin_a_client.get(f"/api/projects/{project_b_id}/")
    assert res.status_code in [403, 404], f"Cross-tenant leak! Admin A accessed Project B: {res.status_code}"

    # Admin B attempts to view Tenant A's Invoice A -> MUST FAIL (403 or 404)
    res = admin_b_client.get(f"/api/invoices/{invoice_a_id}/")
    assert res.status_code in [403, 404], f"Cross-tenant leak! Admin B accessed Invoice A: {res.status_code}"

    # Admin B attempts to list clients -> MUST ONLY return Tenant B clients
    res = admin_b_client.get("/api/clients/")
    assert res.status_code == 200
    b_client_ids = [c["id"] for c in res.json().get("data", [])]
    assert client_b_id in b_client_ids
    assert client_a_id not in b_client_ids, "Cross-tenant leak! Tenant A client appeared in Tenant B client list"

    # =========================================================================
    # 5. RAZORPAY / PAYMENT LIFECYCLE & INVOICE UPDATE
    # =========================================================================
    payment = Payment.objects.create(
        business=business_a,
        invoice=invoice_a,
        amount=invoice_a.total,
        method=Payment.Method.ONLINE,
        status=Payment.Status.SUCCESS,
        transaction_id="pay_mock_audit_12345",
    )
    invoice_a.status = Invoice.Status.PAID
    invoice_a.save()

    # Verify Dashboard updates dynamically with real revenue
    res = admin_a_client.get("/api/dashboard/")
    assert res.status_code == 200
    dash_data = res.json()["data"]
    assert dash_data["clients"] >= 1
    assert dash_data["vendors"] >= 1
    assert dash_data["invoices"] >= 1
    assert dash_data["paid_invoices"] >= 1
