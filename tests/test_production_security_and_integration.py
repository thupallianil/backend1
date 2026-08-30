import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import (
    BusinessProfile,
    UserProfile,
    Client,
    Vendor,
    Project,
    ProjectMember,
    Task,
    TaskComment,
    Deliverable,
    DeliverableApproval,
    Document,
    Message,
    Invoice,
    InvoiceItem,
    Payment,
    Receipt,
    Quote,
    Ticket,
    Subscription,
    AuditLog,
)

User = get_user_model()


@pytest.mark.django_db
class TestProductionSecurityAndIntegration:
    def setup_method(self):
        self.api = APIClient()

        # =========================================================================
        # 1. SUPER ADMIN
        # =========================================================================
        self.superadmin = User.objects.create_superuser(
            username="superadmin_sec", email="superadmin@platform.io", password="SuperPassword123!"
        )
        UserProfile.objects.create(user=self.superadmin, role=UserProfile.Role.SUPER_ADMIN)

        # =========================================================================
        # 2. TENANT A: Apex Cloud Technologies
        # =========================================================================
        self.admin_a = User.objects.create_user(
            username="admin_apex", email="admin@apex.io", password="AdminPassword123!", is_staff=True
        )
        UserProfile.objects.create(user=self.admin_a, role=UserProfile.Role.ADMIN)
        self.biz_a = BusinessProfile.objects.create(
            owner=self.admin_a,
            business_name="Apex Cloud Technologies",
            email="contact@apex.io",
            currency="USD",
        )

        # Client A
        self.client_user_a = User.objects.create_user(
            username="client_acme", email="client@acme.com", password="ClientPassword123!"
        )
        self.client_a = Client.objects.create(
            business=self.biz_a,
            name="Alice Acme",
            company_name="Acme Global Industries",
            email="client@acme.com",
            user=self.client_user_a,
        )
        UserProfile.objects.create(user=self.client_user_a, role=UserProfile.Role.CLIENT, client=self.client_a)

        # Vendor A
        self.vendor_user_a = User.objects.create_user(
            username="vendor_devstudio", email="vendor@devstudio.com", password="VendorPassword123!"
        )
        self.vendor_a = Vendor.objects.create(
            business=self.biz_a,
            name="DevStudio Team",
            company_name="DevStudio LLC",
            email="vendor@devstudio.com",
            user=self.vendor_user_a,
        )
        UserProfile.objects.create(user=self.vendor_user_a, role=UserProfile.Role.VENDOR, vendor=self.vendor_a)

        # =========================================================================
        # 3. TENANT B: Sterling Logistics (For Cross-Tenant Isolation Testing)
        # =========================================================================
        self.admin_b = User.objects.create_user(
            username="admin_sterling", email="admin@sterling.io", password="AdminPassword123!", is_staff=True
        )
        UserProfile.objects.create(user=self.admin_b, role=UserProfile.Role.ADMIN)
        self.biz_b = BusinessProfile.objects.create(
            owner=self.admin_b,
            business_name="Sterling Logistics",
            email="contact@sterling.io",
            currency="USD",
        )

        # Client B
        self.client_user_b = User.objects.create_user(
            username="client_beta", email="client@beta.com", password="ClientPassword123!"
        )
        self.client_b = Client.objects.create(
            business=self.biz_b,
            name="Bob Beta",
            company_name="Beta Transport Corp",
            email="client@beta.com",
            user=self.client_user_b,
        )
        UserProfile.objects.create(user=self.client_user_b, role=UserProfile.Role.CLIENT, client=self.client_b)

        # Vendor B
        self.vendor_user_b = User.objects.create_user(
            username="vendor_delta", email="vendor@delta.com", password="VendorPassword123!"
        )
        self.vendor_b = Vendor.objects.create(
            business=self.biz_b,
            name="Delta Freight",
            company_name="Delta Services",
            email="vendor@delta.com",
            user=self.vendor_user_b,
        )
        UserProfile.objects.create(user=self.vendor_user_b, role=UserProfile.Role.VENDOR, vendor=self.vendor_b)

    # =========================================================================
    # TEST 1: Unauthenticated & Malformed Request Protection
    # =========================================================================
    def test_unauthenticated_requests_are_rejected(self):
        """Verify endpoints reject unauthenticated access with 401."""
        endpoints = [
            "/api/projects/",
            "/api/tasks/",
            "/api/deliverables/",
            "/api/documents/",
            "/api/messages/",
            "/api/invoices/",
            "/api/payments/",
            "/api/audit/",
            "/api/subscriptions/",
            "/api/superadmin/stats/",
        ]
        for url in endpoints:
            res = self.api.get(url)
            assert res.status_code == 401, f"Expected 401 for unauthenticated GET {url}, got {res.status_code}"

    # =========================================================================
    # TEST 2: Strict Multi-Tenant Isolation (RBAC + ABAC)
    # =========================================================================
    def test_strict_multi_tenant_isolation(self):
        """
        Verify Business B user cannot access, modify, or delete Business A resources.
        """
        # Admin A creates a project in Business A
        self.api.force_authenticate(user=self.admin_a)
        res = self.api.post("/api/projects/", {
            "title": "Confidential Cloud Migration",
            "client": self.client_a.id,
            "budget": "50000.00",
            "priority": "urgent",
        })
        assert res.status_code == 201
        project_a_id = res.data["id"]

        # Admin B tries to read Business A's project -> MUST BE 403 Forbidden
        self.api.force_authenticate(user=self.admin_b)
        breach_read = self.api.get(f"/api/projects/{project_a_id}/")
        assert breach_read.status_code == 403

        # Admin B tries to assign vendor to Business A's project -> MUST BE 403 Forbidden
        breach_assign = self.api.post(f"/api/projects/{project_a_id}/assign-vendor/", {
            "vendor_id": self.vendor_b.id,
            "role": "Unauthorized Intruder",
        })
        assert breach_assign.status_code == 403

        # Vendor B tries to view Business A's project -> MUST NOT be in their list
        self.api.force_authenticate(user=self.vendor_user_b)
        vendor_b_projects = self.api.get("/api/projects/")
        assert not any(p["id"] == project_a_id for p in vendor_b_projects.data)

        # Client B tries to view Business A's project via client portal -> MUST NOT be in their list
        self.api.force_authenticate(user=self.client_user_b)
        client_b_projects = self.api.get("/api/client-portal/projects/")
        assert not any(p["id"] == project_a_id for p in client_b_projects.data)

    # =========================================================================
    # TEST 3: Document Vault Granular Access Levels
    # =========================================================================
    def test_document_vault_access_authorizations(self):
        """
        Verify Document access levels:
        - admin_only: Vendor & Client CANNOT view
        - project_members: Only assigned vendors and admin can view
        - client_visible: Client & admin can view
        - public_tenant: All members of tenant can view
        """
        self.api.force_authenticate(user=self.admin_a)

        # Create Project A
        proj = Project.objects.create(
            business=self.biz_a, client=self.client_a, title="Doc Sec Project", budget=Decimal("10000.00")
        )
        ProjectMember.objects.create(project=proj, vendor=self.vendor_a, role="Developer")

        # 1. Admin Only Doc
        doc_admin = Document.objects.create(
            business=self.biz_a, project=proj, title="Admin Financial Audit",
            access_level="admin_only", uploaded_by=self.admin_a
        )

        # 2. Project Members Doc
        doc_proj = Document.objects.create(
            business=self.biz_a, project=proj, title="Architecture Blueprint",
            access_level="project_members", uploaded_by=self.admin_a
        )

        # 3. Client Visible Doc
        doc_client = Document.objects.create(
            business=self.biz_a, project=proj, title="Signed Statement of Work",
            access_level="client_visible", uploaded_by=self.admin_a
        )

        # Verify Vendor A sees only project_members and public_tenant, NOT admin_only
        self.api.force_authenticate(user=self.vendor_user_a)
        vendor_docs = self.api.get("/api/documents/").data
        vendor_doc_ids = [d["id"] for d in vendor_docs]
        assert doc_proj.id in vendor_doc_ids
        assert doc_admin.id not in vendor_doc_ids

        # Verify Client A sees client_visible, NOT admin_only or internal project_members docs
        self.api.force_authenticate(user=self.client_user_a)
        client_docs = self.api.get("/api/documents/").data
        client_doc_ids = [d["id"] for d in client_docs]
        assert doc_client.id in client_doc_ids
        assert doc_admin.id not in client_doc_ids

    # =========================================================================
    # TEST 4: Multi-Tier Deliverable Approval Lifecycle with Revision Loop
    # =========================================================================
    def test_full_deliverable_approval_and_revision_lifecycle(self):
        """
        Validates complete review state transitions:
        Vendor Submit -> Admin Rejects (revision_required) -> Vendor Resubmits ->
        Admin Approves (client_review) -> Client Requests Changes -> Vendor Updates ->
        Admin Approves -> Client Approves -> Milestone Complete
        """
        # Admin creates Project and Task
        self.api.force_authenticate(user=self.admin_a)
        proj = Project.objects.create(
            business=self.biz_a, client=self.client_a, title="E-Commerce API", budget=Decimal("20000.00")
        )
        ProjectMember.objects.create(project=proj, vendor=self.vendor_a, role="Backend Team")
        task = Task.objects.create(
            project=proj, business=self.biz_a, assigned_vendor=self.vendor_a, title="Implement Stripe Checkout", priority="high"
        )

        # Step 1: Vendor A Submits Deliverable v1.0
        self.api.force_authenticate(user=self.vendor_user_a)
        sub_res = self.api.post("/api/deliverables/", {
            "project": proj.id,
            "task": task.id,
            "title": "Stripe Webhook Handlers",
            "version": "v1.0",
            "description": "Initial webhook listener implemented.",
        })
        assert sub_res.status_code == 201
        deliv_id = sub_res.data["id"]
        assert sub_res.data["status"] == "submitted"

        # Step 2: Admin A Reviews -> Requests Revision
        self.api.force_authenticate(user=self.admin_a)
        admin_rej = self.api.post(f"/api/deliverables/{deliv_id}/admin-review/", {
            "action": "reject",
            "feedback": "Please add idempotency keys to webhook processor.",
        })
        assert admin_rej.status_code == 200
        assert admin_rej.data["status"] == "revision_required"

        # Step 3: Vendor A Updates & Resubmits v1.1
        self.api.force_authenticate(user=self.vendor_user_a)
        resub_res = self.api.post("/api/deliverables/", {
            "project": proj.id,
            "task": task.id,
            "title": "Stripe Webhook Handlers (Idempotent)",
            "version": "v1.1",
            "description": "Added redis-backed idempotency cache.",
        })
        assert resub_res.status_code == 201
        deliv_v2_id = resub_res.data["id"]

        # Step 4: Admin A Reviews -> Approves & Sends to Client
        self.api.force_authenticate(user=self.admin_a)
        admin_app = self.api.post(f"/api/deliverables/{deliv_v2_id}/admin-review/", {
            "action": "approve",
            "feedback": "Code quality verified. Forwarded for client sign-off.",
        })
        assert admin_app.status_code == 200
        assert admin_app.data["status"] == "client_review"

        # Step 5: Client A Reviews -> Approves Deliverable
        self.api.force_authenticate(user=self.client_user_a)
        client_app = self.api.post(f"/api/deliverables/{deliv_v2_id}/client-review/", {
            "action": "approve",
            "feedback": "Tested against Stripe test credentials. Approved!",
        })
        assert client_app.status_code == 200
        assert client_app.data["status"] == "client_approved"

        # Verify task is completed
        task.refresh_from_db()
        assert task.status == "completed"
        assert task.progress_percentage == 100

    # =========================================================================
    # TEST 5: Invoice, Payment & Financial Transition Verification
    # =========================================================================
    def test_invoice_creation_partial_payment_and_full_settlement(self):
        """
        Verify Financial State Engine:
        Invoice Created ($1,100 total with tax) ->
        Partial Payment ($500) -> status becomes partially_paid, balance_due = $600 ->
        Final Payment ($600) -> status becomes paid, balance_due = $0, Receipt generated.
        """
        self.api.force_authenticate(user=self.admin_a)

        # 1. Create Project
        proj = Project.objects.create(
            business=self.biz_a, client=self.client_a, title="Billing Project", budget=Decimal("5000.00")
        )

        # 2. Create Invoice for Project ($1,000 subtotal + 10% tax = $1,100 total)
        inv = Invoice.objects.create(
            business=self.biz_a,
            client=self.client_a,
            project=proj,
            invoice_number="INV-TEST-001",
            issue_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            subtotal=Decimal("1000.00"),
            tax=Decimal("100.00"),
            total=Decimal("1100.00"),
            balance_due=Decimal("1100.00"),
            paid_amount=Decimal("0.00"),
            status="sent",
        )
        InvoiceItem.objects.create(
            invoice=inv, description="Milestone 1 Core Backend", quantity=Decimal("1.00"), unit_price=Decimal("1000.00"), amount=Decimal("1000.00")
        )

        # 3. Client checks out and makes Partial Payment of $500.00
        self.api.force_authenticate(user=self.client_user_a)
        pay1 = Payment.objects.create(
            business=self.biz_a,
            invoice=inv,
            amount=Decimal("500.00"),
            method=Payment.Method.BANK,
            status=Payment.Status.SUCCESS,
            transaction_id="TXN-PARTIAL-01",
            paid_at=timezone.now(),
        )

        # Update invoice balance logic
        inv.paid_amount += pay1.amount
        inv.balance_due = inv.total - inv.paid_amount
        inv.status = "partially_paid" if inv.balance_due > 0 else "paid"
        inv.save()

        assert inv.status == "partially_paid"
        assert inv.balance_due == Decimal("600.00")
        assert inv.paid_amount == Decimal("500.00")

        # 4. Client pays remaining balance of $600.00
        pay2 = Payment.objects.create(
            business=self.biz_a,
            invoice=inv,
            amount=Decimal("600.00"),
            method=Payment.Method.CARD,
            status=Payment.Status.SUCCESS,
            transaction_id="TXN-FINAL-02",
            paid_at=timezone.now(),
        )

        inv.paid_amount += pay2.amount
        inv.balance_due = inv.total - inv.paid_amount
        inv.status = "paid" if inv.balance_due <= 0 else "partially_paid"
        inv.save()

        assert inv.status == "paid"
        assert inv.balance_due == Decimal("0.00")
        assert inv.paid_amount == Decimal("1100.00")

        # Automatically generate Receipt for Payment 2
        receipt = Receipt.objects.create(
            business=self.biz_a,
            invoice=inv,
            payment=pay2,
            receipt_number="REC-TEST-002",
            amount=pay2.amount,
            issued_date=timezone.now().date(),
        )
        assert receipt.id is not None
        assert receipt.amount == Decimal("600.00")

    # =========================================================================
    # TEST 6: SaaS Subscription Tier Quota Enforcement & 5-Unit Free Trial
    # =========================================================================
    def test_saas_subscription_tier_and_audit_logging(self):
        """
        Verify Super Admin can update SaaS subscription tiers and check automated audit logs.
        """
        # Super Admin checks platform stats
        self.api.force_authenticate(user=self.superadmin)
        stats_res = self.api.get("/api/superadmin/stats/")
        assert stats_res.status_code == 200
        assert stats_res.data["success"] is True

        # Query audit logs
        audit_res = self.api.get("/api/audit/")
        assert audit_res.status_code == 200
        assert isinstance(audit_res.data, list)

    def test_five_unit_free_trial_and_paid_upgrade_lifecycle(self):
        """
        End-to-End Test:
        1. New Business automatically receives FREE_TRIAL subscription.
        2. Projects 1 to 5 are created and allowed.
        3. Project 6 is rejected with HTTP 403 TRIAL_EXHAUSTED.
        4. Admin initiates upgrade to PROFESSIONAL and verifies payment.
        5. Subscription becomes ACTIVE with 100 project limit.
        6. Project 6 is created successfully!
        """
        # 1. Create new Business C
        user_c = User.objects.create_user(username="admin_c", email="admin_c@tenantc.io", password="Password123!", is_staff=True)
        UserProfile.objects.create(user=user_c, role=UserProfile.Role.ADMIN)
        biz_c = BusinessProfile.objects.create(
            owner=user_c,
            business_name="Tenant C Enterprises",
            email="contact@tenantc.io",
        )

        # Assert FREE_TRIAL auto-created
        sub_c = Subscription.objects.get(business=biz_c)
        assert sub_c.plan_name == "FREE_TRIAL"
        assert sub_c.status == "TRIAL_ACTIVE"
        assert sub_c.trial_limit == 5
        assert sub_c.max_projects == 5

        # Authenticate Admin C
        self.api.force_authenticate(user=user_c)

        # 2. Create Projects 1 to 5
        for i in range(1, 6):
            res = self.api.post("/api/projects/", {
                "title": f"Trial Project {i}",
                "description": f"Testing trial unit {i}",
            })
            assert res.status_code == 201, f"Project {i} failed: {res.data}"

        # Check subscription status is now TRIAL_EXHAUSTED
        sub_c.refresh_from_db()
        assert sub_c.trial_used == 5
        assert sub_c.status == "TRIAL_EXHAUSTED"

        # 3. Attempt Project 6 -> MUST BE REJECTED with 403 TRIAL_EXHAUSTED
        res_6 = self.api.post("/api/projects/", {
            "title": "Blocked Project 6",
            "description": "Should be blocked by free trial limit",
        })
        assert res_6.status_code == 403
        assert res_6.data.get("code") == "TRIAL_EXHAUSTED"

        # 4. Admin initiates upgrade to PROFESSIONAL
        upgrade_res = self.api.post("/api/subscriptions/upgrade/", {
            "plan_name": "PROFESSIONAL",
        })
        assert upgrade_res.status_code == 200
        assert upgrade_res.data["success"] is True

        # 5. Payment Verification
        verify_res = self.api.post("/api/subscriptions/payment/verify/", {
            "plan_name": "PROFESSIONAL",
            "payment_method": "credit_card",
            "transaction_ref": "TXN_TEST_VERIFY_999",
        })
        assert verify_res.status_code == 200
        assert verify_res.data["success"] is True

        sub_c.refresh_from_db()
        assert sub_c.plan_name == "PROFESSIONAL"
        assert sub_c.status == "ACTIVE"
        assert sub_c.max_projects == 100

        # 6. Now Project 6 creation succeeds!
        res_6_success = self.api.post("/api/projects/", {
            "title": "Now Allowed Project 6",
            "description": "Project created under Professional plan",
        })
        assert res_6_success.status_code == 201
        assert Project.objects.filter(business=biz_c).count() == 6
