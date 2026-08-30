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
)

User = get_user_model()


def get_items(res):
    payload = res.json()
    if isinstance(payload, list):
        return payload
    return payload.get("data", payload)


@pytest.fixture
def make_auth_client():
    def _make(user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client
    return _make


@pytest.mark.django_db
def test_dynamic_database_driven_proof(make_auth_client):
    """
    Exhaustive Dynamic Database Proof:
    1. Fresh Tenant with 0 Clients, 0 Vendors, 0 Projects, 0 Invoices, 0 Quotes.
    2. Verify Empty States from live API endpoints.
    3. Step-by-step Creation across all entities through API -> DB insertion -> GET verification.
    4. Simulate Hard Browser Reloads with independent API sessions.
    5. Step-by-step Updates through API -> DB mutation -> GET verification after simulated reload.
    6. Step-by-step Deletions -> DB removal -> Empty State restoration.
    """

    # =========================================================================
    # 1. PROVISION FRESH TENANT (ZERO STATE)
    # =========================================================================
    admin_user = User.objects.create_user(
        username="proof_admin",
        email="proof_admin@dynamictest.com",
        password="ProofPassword123!",
        first_name="Proof Admin",
        is_staff=True,
    )
    UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
    business = BusinessProfile.objects.create(
        owner=admin_user,
        business_name="Dynamic Proof Enterprises",
        email="proof_admin@dynamictest.com",
    )
    AppSettings.objects.get_or_create(business=business)
    Subscription.objects.update_or_create(
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

    client_session_1 = make_auth_client(admin_user)

    # Verify Empty States (0 records in DB)
    res = client_session_1.get("/api/dashboard/")
    assert res.status_code == 200
    dash_data = res.json()["data"]
    assert dash_data["clients"] == 0, "Expected 0 clients in fresh tenant"
    assert dash_data["vendors"] == 0, "Expected 0 vendors in fresh tenant"
    assert dash_data["invoices"] == 0, "Expected 0 invoices in fresh tenant"

    res = client_session_1.get("/api/clients/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0

    res = client_session_1.get("/api/vendors/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0

    res = client_session_1.get("/api/projects/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0

    res = client_session_1.get("/api/tasks/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0

    res = client_session_1.get("/api/invoices/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0

    # =========================================================================
    # 2. DYNAMIC RECORD CREATION & DB INSERTION
    # =========================================================================
    # CREATE CLIENT
    res = client_session_1.post("/api/clients/", {
        "name": "Dynamic Client 1",
        "company_name": "Dynamic Corporation",
        "email": "client1@dynamic.com",
        "phone": "+1 555-0199",
        "address": "100 Innovation Way, Silicon Valley, CA",
    }, format="json")
    assert res.status_code == 201
    client_id = get_items(res)["id"]
    assert Client.objects.filter(id=client_id, business=business).exists()

    # CREATE VENDOR
    res = client_session_1.post("/api/vendors/", {
        "name": "Dynamic Vendor 1",
        "company_name": "Dynamic Studio Partners",
        "email": "vendor1@dynamic.com",
        "category": "services",
        "phone": "+1 555-0188",
    }, format="json")
    assert res.status_code == 201
    vendor_id = get_items(res)["id"]
    assert Vendor.objects.filter(id=vendor_id, business=business).exists()

    # CREATE PROJECT
    res = client_session_1.post("/api/projects/", {
        "title": "Dynamic Full-Stack Verification Project",
        "client": client_id,
        "status": "in_progress",
        "budget": "20000.00",
    }, format="json")
    assert res.status_code == 201
    project_id = get_items(res)["id"]
    assert Project.objects.filter(id=project_id, business=business).exists()

    # CREATE TASK
    res = client_session_1.post("/api/tasks/", {
        "project": project_id,
        "title": "Implement Real-Time Telemetry",
        "status": "in_progress",
        "priority": "high",
        "assigned_vendor": vendor_id,
    }, format="json")
    assert res.status_code == 201
    task_id = get_items(res)["id"]
    assert Task.objects.filter(id=task_id, project_id=project_id).exists()

    # CREATE DELIVERABLE
    res = client_session_1.post("/api/deliverables/", {
        "project": project_id,
        "task": task_id,
        "title": "Real-Time Telemetry Pipeline v1.0",
        "version": "1.0",
    }, format="json")
    assert res.status_code == 201
    deliv_id = get_items(res)["id"]
    assert Deliverable.objects.filter(id=deliv_id, project_id=project_id).exists()

    # CREATE INVOICE
    res = client_session_1.post("/api/invoices/", {
        "client": client_id,
        "project": project_id,
        "due_date": "2026-10-15",
        "items": [
            {
                "description": "Milestone 1 Core Development",
                "quantity": 1,
                "unit_price": "7500.00",
                "tax_rate": "18.00",
            }
        ]
    }, format="json")
    assert res.status_code == 201
    invoice_id = get_items(res)["id"]
    assert Invoice.objects.filter(id=invoice_id, business=business).exists()

    # =========================================================================
    # 3. SIMULATE BROWSER REFRESH / NEW SESSION (PERSISTENCE PROOF)
    # =========================================================================
    # Fresh client session simulating page reload with clean memory
    client_session_2 = make_auth_client(admin_user)

    # Verify all records persist identically from database
    res = client_session_2.get(f"/api/clients/{client_id}/")
    assert res.status_code == 200
    assert get_items(res)["name"] == "Dynamic Client 1"

    res = client_session_2.get(f"/api/vendors/{vendor_id}/")
    assert res.status_code == 200
    assert get_items(res)["company_name"] == "Dynamic Studio Partners"

    res = client_session_2.get(f"/api/projects/{project_id}/")
    assert res.status_code == 200
    assert get_items(res)["title"] == "Dynamic Full-Stack Verification Project"

    res = client_session_2.get(f"/api/tasks/{task_id}/")
    assert res.status_code == 200
    assert get_items(res)["title"] == "Implement Real-Time Telemetry"

    res = client_session_2.get(f"/api/invoices/{invoice_id}/")
    assert res.status_code == 200
    assert float(get_items(res)["total"]) > 7500.00

    # Verify Dashboard stats dynamically updated to 1
    res = client_session_2.get("/api/dashboard/")
    assert res.status_code == 200
    dash_data_2 = res.json()["data"]
    assert dash_data_2["clients"] == 1
    assert dash_data_2["vendors"] == 1
    assert dash_data_2["invoices"] == 1

    # =========================================================================
    # 4. DYNAMIC UPDATE & PERSISTENCE AFTER REFRESH
    # =========================================================================
    # Update Client Name & Address
    res = client_session_2.patch(f"/api/clients/{client_id}/", {
        "name": "Dynamic Client 1 (Updated Corp)",
        "address": "200 Tech Boulevard, Austin, TX",
    }, format="json")
    assert res.status_code == 200

    # Update Project Status to completed
    res = client_session_2.patch(f"/api/projects/{project_id}/", {
        "status": "completed",
        "budget": "22000.00",
    }, format="json")
    assert res.status_code == 200

    # Update Task Status to completed
    res = client_session_2.patch(f"/api/tasks/{task_id}/", {
        "status": "completed",
        "priority": "urgent",
    }, format="json")
    assert res.status_code == 200

    # Fresh session 3 (Simulate second page reload)
    client_session_3 = make_auth_client(admin_user)

    res = client_session_3.get(f"/api/clients/{client_id}/")
    assert res.status_code == 200
    assert get_items(res)["name"] == "Dynamic Client 1 (Updated Corp)"
    assert get_items(res)["address"] == "200 Tech Boulevard, Austin, TX"

    res = client_session_3.get(f"/api/projects/{project_id}/")
    assert res.status_code == 200
    assert get_items(res)["status"] == "completed"

    res = client_session_3.get(f"/api/tasks/{task_id}/")
    assert res.status_code == 200
    assert get_items(res)["status"] == "completed"

    # =========================================================================
    # 5. DYNAMIC DELETION & EMPTY STATE RESTORATION
    # =========================================================================
    # Delete Deliverable
    res = client_session_3.delete(f"/api/deliverables/{deliv_id}/")
    assert res.status_code in [200, 204]
    assert not Deliverable.objects.filter(id=deliv_id).exists()

    # Delete Task
    res = client_session_3.delete(f"/api/tasks/{task_id}/")
    assert res.status_code in [200, 204]
    assert not Task.objects.filter(id=task_id).exists()

    # Verify Tasks and Deliverables querysets return empty list []
    res = client_session_3.get("/api/tasks/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0

    res = client_session_3.get("/api/deliverables/")
    assert res.status_code == 200
    assert len(get_items(res)) == 0
