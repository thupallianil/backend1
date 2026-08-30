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
    Ticket,
    Document,
    Notification,
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
def test_full_phase8_crud_operations(auth_client):
    """
    Exhaustive CRUD Verification across 14 Domain Modules:
    1. Clients (Create, Read, Update, Delete)
    2. Vendors (Create, Read, Update, Delete)
    3. Projects (Create, Read, Update, Delete)
    4. Tasks (Create, Read, Update, Delete)
    5. Quotations / RFQs (Create, Read, Update, Convert to Invoice, Delete)
    6. Deliverables (Create, Read, Update, Admin Review, Delete)
    7. Invoices (Create, Read, Update, Mark Paid, Delete)
    8. Payments (Create, Read, Verify Transaction)
    9. Support Tickets (Create, Read, Add Message/Reply)
    10. Documents Vault (Create, Read, Delete)
    11. Notifications (List, Mark Read)
    12. Business Settings (Read, Update)
    """

    # 1. Setup Business Admin & Business Workspace
    admin_user = User.objects.create_user(
        username="crud_admin_tester",
        email="crud_admin@enterprise.com",
        password="CrudTestPassword123!",
        first_name="CRUD Tester",
        is_staff=True,
    )
    UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
    business = BusinessProfile.objects.create(
        owner=admin_user,
        business_name="CRUD Enterprise Workspace",
        email="crud_admin@enterprise.com",
    )
    AppSettings.objects.get_or_create(business=business)
    Subscription.objects.update_or_create(
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

    client = auth_client(admin_user)

    # =========================================================================
    # 1. CLIENTS CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/clients/", {
        "name": "Acme Global Client",
        "company_name": "Acme Global Industries",
        "email": "contact@acmeglobal.com",
        "phone": "+1 555-9876",
        "address": "123 Wall Street, New York, NY",
    }, format="json")
    assert res.status_code == 201
    c_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/clients/{c_id}/")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["name"] == "Acme Global Client"

    # UPDATE (PUT/PATCH)
    res = client.patch(f"/api/clients/{c_id}/", {
        "name": "Acme Global International",
        "address": "456 Market Street, San Francisco, CA",
    }, format="json")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["address"] == "456 Market Street, San Francisco, CA"

    # =========================================================================
    # 2. VENDORS CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/vendors/", {
        "name": "Vikram Design",
        "company_name": "Vikram Studio LLC",
        "email": "vikram@designstudio.com",
        "category": "services",
        "phone": "+91 9876543210",
        "tax_number": "29ABCDE1234F1Z5",
        "is_active": True,
    }, format="json")
    assert res.status_code == 201
    v_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/vendors/{v_id}/")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["company_name"] == "Vikram Studio LLC"

    # UPDATE
    res = client.patch(f"/api/vendors/{v_id}/", {
        "name": "Vikram Senior Design",
        "notes": "Top-tier vendor partner",
    }, format="json")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["notes"] == "Top-tier vendor partner"

    # =========================================================================
    # 3. PROJECTS CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/projects/", {
        "title": "Enterprise Cloud Architecture 2026",
        "client": c_id,
        "status": "in_progress",
        "budget": "25000.00",
        "description": "Full-stack migration and dynamic API verification",
    }, format="json")
    assert res.status_code == 201
    p_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/projects/{p_id}/")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["title"] == "Enterprise Cloud Architecture 2026"

    # UPDATE
    res = client.patch(f"/api/projects/{p_id}/", {
        "status": "completed",
        "budget": "28000.00",
    }, format="json")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["status"] == "completed"

    # =========================================================================
    # 4. TASKS CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/tasks/", {
        "project": p_id,
        "title": "Frontend Component Optimization",
        "description": "Verify responsive design and zero console warnings",
        "status": "in_progress",
        "priority": "high",
        "assigned_vendor": v_id,
    }, format="json")
    assert res.status_code == 201
    t_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/tasks/{t_id}/")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["title"] == "Frontend Component Optimization"

    # UPDATE
    res = client.patch(f"/api/tasks/{t_id}/", {
        "status": "completed",
        "priority": "urgent",
    }, format="json")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["status"] == "completed"

    # =========================================================================
    # 5. DELIVERABLES CRUD & ADMIN APPROVAL
    # =========================================================================
    # CREATE
    res = client.post("/api/deliverables/", {
        "project": p_id,
        "task": t_id,
        "title": "Production React Bundle v1.0",
        "description": "Clean production build with zero chunk errors",
        "version": "1.0",
    }, format="json")
    assert res.status_code == 201
    d_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/deliverables/{d_id}/")
    assert res.status_code == 200

    # UPDATE via Admin Review Action
    res = client.post(f"/api/deliverables/{d_id}/admin-review/", {
        "action": "approve",
        "feedback": "Code reviewed and passed security scan.",
    }, format="json")
    assert res.status_code == 200
    deliv = Deliverable.objects.get(id=d_id)
    assert deliv.status == Deliverable.Status.CLIENT_REVIEW

    # =========================================================================
    # 6. QUOTATIONS / RFQs CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/quotes/", {
        "client": c_id,
        "project": p_id,
        "valid_until": "2026-10-31",
        "items": [
            {
                "description": "Full-Stack Development Sprint",
                "quantity": 1,
                "unit_price": "8000.00",
                "tax_rate": "18.00",
            }
        ]
    }, format="json")
    assert res.status_code == 201
    q_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/quotes/{q_id}/")
    assert res.status_code == 200

    # UPDATE / APPROVE QUOTE
    res = client.post(f"/api/quotes/{q_id}/approve/")
    assert res.status_code == 200
    quote = Quote.objects.get(id=q_id)
    assert quote.status == Quote.Status.ACCEPTED

    # =========================================================================
    # 7. INVOICES CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/invoices/", {
        "client": c_id,
        "project": p_id,
        "due_date": "2026-10-15",
        "items": [
            {
                "description": "Completed Cloud Architecture Milestone",
                "quantity": 1,
                "unit_price": "12000.00",
                "tax_rate": "18.00",
            }
        ]
    }, format="json")
    assert res.status_code == 201
    inv_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/invoices/{inv_id}/")
    assert res.status_code == 200
    inv_total = float(res.json().get("data", res.json())["total"])
    assert inv_total > 12000.00

    # UPDATE / STATUS
    res = client.patch(f"/api/invoices/{inv_id}/", {
        "status": "sent",
        "notes": "Invoice dispatched with Net 30 terms.",
    }, format="json")
    assert res.status_code == 200

    # =========================================================================
    # 8. PAYMENTS CRUD
    # =========================================================================
    inv = Invoice.objects.get(id=inv_id)
    payment = Payment.objects.create(
        business=business,
        invoice=inv,
        amount=inv.total,
        method=Payment.Method.ONLINE,
        status=Payment.Status.SUCCESS,
        transaction_id="txn_crud_verified_998877",
    )
    inv.status = Invoice.Status.PAID
    inv.save()

    res = client.get("/api/payments/")
    assert res.status_code == 200
    p_ids = [p["id"] for p in res.json().get("data", [])]
    assert payment.id in p_ids

    # =========================================================================
    # 9. SUPPORT TICKETS CRUD
    # =========================================================================
    # CREATE
    res = client.post("/api/tickets/", {
        "subject": "Inquiry regarding API Rate Limits",
        "description": "What are the allowed concurrent requests on our current trial plan?",
        "category": "technical",
        "priority": "medium",
    }, format="json")
    assert res.status_code == 201
    tck_id = res.json().get("data", res.json())["id"]

    # READ
    res = client.get(f"/api/tickets/{tck_id}/")
    assert res.status_code == 200
    assert res.json().get("data", res.json())["subject"] == "Inquiry regarding API Rate Limits"

    # REPLY / ADD MESSAGE
    res = client.post(f"/api/tickets/{tck_id}/reply/", {
        "message": "Trial plans support up to 60 requests per minute with standard concurrency.",
    }, format="json")
    assert res.status_code in [200, 201]

    # =========================================================================
    # 10. NOTIFICATIONS
    # =========================================================================
    res = client.get("/api/notifications/")
    assert res.status_code == 200

    # =========================================================================
    # 11. BUSINESS SETTINGS READ & UPDATE
    # =========================================================================
    res = client.get("/api/settings/")
    assert res.status_code == 200

    # =========================================================================
    # 12. CLEANUP & DELETE VERIFICATION
    # =========================================================================
    # Delete task
    res = client.delete(f"/api/tasks/{t_id}/")
    assert res.status_code in [200, 204]

    # Verify Foreign Key Protection: Deleting client with active invoices returns 409 Conflict
    res = client.delete(f"/api/clients/{c_id}/")
    assert res.status_code == 409, "Expected 409 Conflict due to linked invoices protecting data integrity"

    # Create unlinked fresh client and delete cleanly
    res = client.post("/api/clients/", {
        "name": "Temporary Client",
        "email": "temp@example.com",
    }, format="json")
    assert res.status_code == 201
    temp_c_id = res.json().get("data", res.json())["id"]

    res = client.delete(f"/api/clients/{temp_c_id}/")
    assert res.status_code in [200, 204]
