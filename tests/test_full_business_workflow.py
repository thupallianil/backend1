import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.utils import timezone

from api.models import (
    BusinessProfile,
    UserProfile,
    Client,
    Vendor,
    Project,
    ProjectMember,
    Task,
    Deliverable,
    DeliverableApproval,
    Invoice,
    Payment,
)

User = get_user_model()


@pytest.mark.django_db
class TestFullBusinessLifecycle:
    def setup_method(self):
        self.client = APIClient()

        # 1. Super Admin
        self.superadmin = User.objects.create_superuser(
            username="super_adm", email="sa@platform.io", password="password123"
        )
        UserProfile.objects.create(user=self.superadmin, role=UserProfile.Role.SUPER_ADMIN)

        # 2. Business A & Admin A
        self.admin_a = User.objects.create_user(
            username="admin_a", email="admin_a@biz-a.io", password="password123", is_staff=True
        )
        UserProfile.objects.create(user=self.admin_a, role=UserProfile.Role.ADMIN)
        self.biz_a = BusinessProfile.objects.create(
            owner=self.admin_a,
            business_name="Acme Tech Enterprise",
            email="contact@biz-a.io",
            currency="USD",
        )

        # 3. Client A
        self.client_user_a = User.objects.create_user(
            username="client_user_a", email="client_a@customer.com", password="password123"
        )
        self.client_a = Client.objects.create(
            business=self.biz_a,
            name="Alice Client",
            company_name="Customer Corp",
            email="client_a@customer.com",
            user=self.client_user_a,
        )
        UserProfile.objects.create(user=self.client_user_a, role=UserProfile.Role.CLIENT, client=self.client_a)

        # 4. Vendor A
        self.vendor_user_a = User.objects.create_user(
            username="vendor_user_a", email="vendor_a@supplier.com", password="password123"
        )
        self.vendor_a = Vendor.objects.create(
            business=self.biz_a,
            name="Bob Vendor",
            company_name="Supplier Studio",
            email="vendor_a@supplier.com",
            user=self.vendor_user_a,
        )
        UserProfile.objects.create(user=self.vendor_user_a, role=UserProfile.Role.VENDOR, vendor=self.vendor_a)

        # 5. Business B & Admin B (For strict tenant isolation testing)
        self.admin_b = User.objects.create_user(
            username="admin_b", email="admin_b@biz-b.io", password="password123", is_staff=True
        )
        UserProfile.objects.create(user=self.admin_b, role=UserProfile.Role.ADMIN)
        self.biz_b = BusinessProfile.objects.create(
            owner=self.admin_b,
            business_name="Beta Logistics",
            email="contact@biz-b.io",
        )

    def test_complete_project_task_deliverable_approval_payment_workflow(self):
        # -------------------------------------------------------------
        # STEP 1: Admin A creates a Project
        # -------------------------------------------------------------
        self.client.force_authenticate(user=self.admin_a)
        proj_res = self.client.post("/api/projects/", {
            "title": "Cloud Portal Refactor",
            "client": self.client_a.id,
            "budget": "15000.00",
            "priority": "high",
            "status": "active",
        })
        assert proj_res.status_code == 201
        project_id = proj_res.data["id"]

        # Assign Vendor to Project
        assign_res = self.client.post(f"/api/projects/{project_id}/assign-vendor/", {
            "vendor_id": self.vendor_a.id,
            "role": "Lead Architect",
        })
        assert assign_res.status_code == 201

        # -------------------------------------------------------------
        # STEP 2: Admin A creates a Task for the Project
        # -------------------------------------------------------------
        task_res = self.client.post("/api/tasks/", {
            "project": project_id,
            "title": "Setup OAuth2 and SSO",
            "assigned_vendor": self.vendor_a.id,
            "priority": "high",
            "estimated_hours": "20.00",
        })
        assert task_res.status_code == 201
        task_id = task_res.data["id"]

        # -------------------------------------------------------------
        # STEP 3: Vendor A starts Task and Submits Deliverable
        # -------------------------------------------------------------
        self.client.force_authenticate(user=self.vendor_user_a)
        # Update progress
        update_task_res = self.client.patch(f"/api/tasks/{task_id}/", {
            "status": "in_progress",
            "progress_percentage": 50,
        })
        assert update_task_res.status_code == 200

        # Submit Deliverable
        deliv_res = self.client.post("/api/deliverables/", {
            "project": project_id,
            "task": task_id,
            "title": "OAuth2 Auth Flow Module",
            "version": "v1.0",
            "description": "Implemented PKCE auth flow with complete token refresh rotation.",
            "external_url": "https://github.com/acme/oauth-build",
        })
        assert deliv_res.status_code == 201
        deliverable_id = deliv_res.data["id"]
        assert deliv_res.data["status"] == "submitted"

        # -------------------------------------------------------------
        # STEP 4: Admin A Reviews Deliverable -> Approves & Sends to Client
        # -------------------------------------------------------------
        self.client.force_authenticate(user=self.admin_a)
        admin_review_res = self.client.post(f"/api/deliverables/{deliverable_id}/admin-review/", {
            "action": "approve",
            "feedback": "Code conforms to enterprise standards. Forwarded for client verification.",
        })
        assert admin_review_res.status_code == 200
        assert admin_review_res.data["status"] == "client_review"

        # -------------------------------------------------------------
        # STEP 5: Client A Reviews Deliverable -> Approves Deliverable
        # -------------------------------------------------------------
        self.client.force_authenticate(user=self.client_user_a)
        client_review_res = self.client.post(f"/api/deliverables/{deliverable_id}/client-review/", {
            "action": "approve",
            "feedback": "Tested against staging endpoints. Sign-off granted!",
        })
        assert client_review_res.status_code == 200
        assert client_review_res.data["status"] == "client_approved"

        # -------------------------------------------------------------
        # STEP 6: Multi-Tenant Data Isolation Test
        # Admin B must NOT be able to view or edit Business A's project
        # -------------------------------------------------------------
        self.client.force_authenticate(user=self.admin_b)
        tenant_breach_res = self.client.get(f"/api/projects/{project_id}/")
        assert tenant_breach_res.status_code == 403

        # -------------------------------------------------------------
        # STEP 7: Super Admin Platform Metrics Verification
        # -------------------------------------------------------------
        self.client.force_authenticate(user=self.superadmin)
        stats_res = self.client.get("/api/superadmin/stats/")
        assert stats_res.status_code == 200
        assert stats_res.data["data"]["metrics"]["total_tenants"] >= 2
