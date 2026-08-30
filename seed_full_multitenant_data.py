import os
import django
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
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
    Invoice,
    InvoiceItem,
    Payment,
    Receipt,
    Document,
    Message,
    AuditLog,
    Subscription,
    Notification,
    AppSettings,
)

User = get_user_model()


def seed():
    print("[*] Seeding complete multi-tenant platform database...")

    # 0. Primary Super Admin (thupallianil12@gmail.com)
    sa1, _ = User.objects.get_or_create(
        username="thupallianil12",
        defaults={
            "email": "thupallianil12@gmail.com",
            "first_name": "THUPALLI ANIL",
            "last_name": "KUMAR",
            "is_superuser": True,
            "is_staff": True,
            "is_active": True,
        }
    )
    sa1.email = "thupallianil12@gmail.com"
    sa1.is_superuser = True
    sa1.is_staff = True
    sa1.is_active = True
    sa1.set_password("SuperAdmin@123")
    sa1.save()
    UserProfile.objects.update_or_create(
        user=sa1,
        defaults={"role": "super_admin", "phone": "+91 9876543210"}
    )
    print("[+] Primary Super Admin ready: thupallianil12@gmail.com / SuperAdmin@123")

    # 0.1 Primary Admin (thupallianil012345@gmail.com)
    ad1, _ = User.objects.get_or_create(
        username="thupallianil012345",
        defaults={
            "email": "thupallianil012345@gmail.com",
            "first_name": "Anil",
            "last_name": "Kumar",
            "is_staff": True,
            "is_superuser": False,
            "is_active": True,
        }
    )
    ad1.email = "thupallianil012345@gmail.com"
    ad1.is_staff = True
    ad1.is_active = True
    ad1.set_password("Admin@123")
    ad1.save()
    UserProfile.objects.update_or_create(
        user=ad1,
        defaults={"role": "admin", "phone": "+91 9876543211"}
    )
    primary_biz, _ = BusinessProfile.objects.update_or_create(
        owner=ad1,
        defaults={
            "business_name": "rrr",
            "legal_name": "RRR Enterprises",
            "business_type": "Technology & Software",
            "email": "thupallianil012345@gmail.com",
            "currency": "INR",
            "is_active": True,
            "status": "active",
        }
    )
    AppSettings.objects.get_or_create(business=primary_biz)
    Subscription.objects.update_or_create(
        business=primary_biz,
        defaults={
            "plan_name": "STARTER PLAN",
            "status": "active",
            "monthly_price": Decimal("0.00"),
            "max_projects": 20,
            "max_users": 5,
        }
    )
    print("[+] Primary Admin ready: thupallianil012345@gmail.com / Admin@123")

    # 0.2 Primary Vendor (thupallianil@gmail.com)
    vn1, _ = User.objects.get_or_create(
        username="thupallianil",
        defaults={
            "email": "thupallianil@gmail.com",
            "first_name": "Anil",
            "last_name": "Vendor",
            "is_active": True,
        }
    )
    vn1.email = "thupallianil@gmail.com"
    vn1.is_active = True
    vn1.set_password("Admin@123")
    vn1.save()
    UserProfile.objects.update_or_create(
        user=vn1,
        defaults={"role": "vendor", "phone": "+91 9876543212"}
    )
    Vendor.objects.update_or_create(
        email="thupallianil@gmail.com",
        defaults={
            "name": "Anil Vendor",
            "company_name": "Anil Cloud Logistics",
            "business": primary_biz,
            "user": vn1,
            "status": "active",
        }
    )
    print("[+] Primary Vendor ready: thupallianil@gmail.com / Admin@123")

    # 0.3 Primary Client (thupallianil108@gmail.com)
    cl1, _ = User.objects.get_or_create(
        username="thupallianil108",
        defaults={
            "email": "thupallianil108@gmail.com",
            "first_name": "Anil",
            "last_name": "Client",
            "is_active": True,
        }
    )
    cl1.email = "thupallianil108@gmail.com"
    cl1.is_active = True
    cl1.set_password("Admin@123")
    cl1.save()
    UserProfile.objects.update_or_create(
        user=cl1,
        defaults={"role": "client", "phone": "+91 9876543213"}
    )
    Client.objects.update_or_create(
        email="thupallianil108@gmail.com",
        defaults={
            "name": "Anil Client",
            "company_name": "Anil Global Enterprises",
            "business": primary_biz,
            "user": cl1,
            "status": "active",
        }
    )
    print("[+] Primary Client ready: thupallianil108@gmail.com / Admin@123")

    # 1. Global Super Admin
    superadmin_user, _ = User.objects.get_or_create(
        username="admin_invoiceflow",
        defaults={
            "email": "admin@invoiceflow.com",
            "first_name": "System",
            "last_name": "Admin",
            "is_superuser": True,
            "is_staff": True,
            "is_active": True,
        }
    )
    superadmin_user.set_password("Admin@123")
    superadmin_user.is_superuser = True
    superadmin_user.is_staff = True
    superadmin_user.is_active = True
    superadmin_user.save()

    UserProfile.objects.update_or_create(
        user=superadmin_user,
        defaults={"role": "super_admin", "phone": "+1 800 555 0199"}
    )
    print("[+] Global Super Admin ready: admin@invoiceflow.com / Admin@123")

    # 2. Business 1: Apex Cloud Technologies
    admin1_user, _ = User.objects.get_or_create(
        username="apex_admin",
        defaults={
            "email": "admin@apextech.io",
            "first_name": "Marcus",
            "last_name": "Sterling",
            "is_staff": True,
            "is_superuser": False,
        }
    )
    admin1_user.set_password("Admin123!")
    admin1_user.save()

    UserProfile.objects.update_or_create(
        user=admin1_user,
        defaults={"role": UserProfile.Role.ADMIN, "phone": "+1 415 555 2671"}
    )

    biz1, _ = BusinessProfile.objects.update_or_create(
        owner=admin1_user,
        defaults={
            "business_name": "Apex Cloud Technologies",
            "legal_name": "Apex Cloud Technologies Inc.",
            "business_type": "Enterprise Software & Cloud Engineering",
            "registration_number": "REG-APX-88912",
            "email": "contact@apextech.io",
            "phone": "+1 415 555 2670",
            "website": "https://apextech.io",
            "address": "100 Market St, Suite 400",
            "city": "San Francisco",
            "state": "California",
            "country": "United States",
            "postal_code": "94105",
            "currency": "USD",
            "is_active": True,
            "status": "active",
        }
    )
    AppSettings.objects.get_or_create(business=biz1)

    Subscription.objects.update_or_create(
        business=biz1,
        defaults={
            "plan_name": "Enterprise Plus",
            "status": Subscription.Status.ACTIVE,
            "monthly_price": Decimal("199.00"),
            "max_projects": 100,
            "max_users": 50,
            "valid_until": timezone.localdate() + timezone.timedelta(days=365)
        }
    )
    print("[+] Business 1 ready: Apex Cloud Technologies (Admin: admin@apextech.io / Admin123!)")

    # 3. Client 1 for Business 1
    client1_user, _ = User.objects.get_or_create(
        username="acme_client",
        defaults={
            "email": "client@acmecorp.com",
            "first_name": "Eleanor",
            "last_name": "Rigby",
            "is_staff": False,
            "is_superuser": False,
        }
    )
    client1_user.set_password("Client123!")
    client1_user.save()

    client1, _ = Client.objects.update_or_create(
        business=biz1,
        email="client@acmecorp.com",
        defaults={
            "name": "Eleanor Rigby",
            "company_name": "Acme Global Industries",
            "phone": "+1 212 555 9021",
            "address": "742 Evergreen Terrace, New York, NY",
            "notes": "Key enterprise client for retail portal modernization.",
            "is_active": True,
            "user": client1_user,
        }
    )
    UserProfile.objects.update_or_create(
        user=client1_user,
        defaults={"role": UserProfile.Role.CLIENT, "client": client1, "phone": "+1 212 555 9021"}
    )
    print("[+] Client 1 ready: client@acmecorp.com / Client123!")

    # 4. Vendor 1 for Business 1
    vendor1_user, _ = User.objects.get_or_create(
        username="devstudio_vendor",
        defaults={
            "email": "vendor@devstudio.com",
            "first_name": "Vikram",
            "last_name": "Sharma",
            "is_staff": False,
            "is_superuser": False,
        }
    )
    vendor1_user.set_password("Vendor123!")
    vendor1_user.save()

    vendor1, _ = Vendor.objects.update_or_create(
        business=biz1,
        email="vendor@devstudio.com",
        defaults={
            "name": "Vikram Sharma",
            "company_name": "DevStudio Solutions",
            "phone": "+1 650 555 4123",
            "category": Vendor.Category.SERVICES,
            "tax_number": "TAX-DEV-9921",
            "address": "450 University Ave, Palo Alto, CA",
            "city": "Palo Alto",
            "state": "California",
            "country": "United States",
            "payment_terms": "Net 15",
            "is_active": True,
            "user": vendor1_user,
        }
    )
    UserProfile.objects.update_or_create(
        user=vendor1_user,
        defaults={"role": UserProfile.Role.VENDOR, "vendor": vendor1, "phone": "+1 650 555 4123"}
    )
    print("[+] Vendor 1 ready: vendor@devstudio.com / Vendor123!")

    # 5. Projects for Business 1
    proj1, _ = Project.objects.update_or_create(
        business=biz1,
        code="PRJ-ECOM-01",
        defaults={
            "client": client1,
            "created_by": admin1_user,
            "title": "NextGen E-Commerce Modernization",
            "description": "Full-stack microservices re-platforming with real-time inventory and headless checkout.",
            "status": Project.Status.ACTIVE,
            "priority": Project.Priority.HIGH,
            "budget": Decimal("45000.00"),
            "start_date": timezone.localdate() - timezone.timedelta(days=20),
            "end_date": timezone.localdate() + timezone.timedelta(days=40),
            "progress_percentage": 65,
        }
    )
    ProjectMember.objects.get_or_create(project=proj1, vendor=vendor1, defaults={"role": "Lead Full-Stack Vendor"})

    proj2, _ = Project.objects.update_or_create(
        business=biz1,
        code="PRJ-CLOUD-02",
        defaults={
            "client": client1,
            "created_by": admin1_user,
            "title": "Multi-Region Cloud Infrastructure Migration",
            "description": "Zero-downtime database migration to Kubernetes clusters across US-East and EU-West.",
            "status": Project.Status.IN_PROGRESS,
            "priority": Project.Priority.URGENT,
            "budget": Decimal("28000.00"),
            "start_date": timezone.localdate() - timezone.timedelta(days=10),
            "end_date": timezone.localdate() + timezone.timedelta(days=25),
            "progress_percentage": 40,
        }
    )
    ProjectMember.objects.get_or_create(project=proj2, vendor=vendor1, defaults={"role": "Cloud DevOps Vendor"})

    # 6. Tasks for Projects
    task1, _ = Task.objects.update_or_create(
        project=proj1,
        title="Implement High-Conversion Checkout Flow",
        defaults={
            "business": biz1,
            "assigned_vendor": vendor1,
            "created_by": admin1_user,
            "description": "Build dynamic one-page checkout with Apple Pay, Google Pay, and Stripe elements.",
            "priority": Task.Priority.HIGH,
            "status": Task.Status.COMPLETED,
            "start_date": timezone.localdate() - timezone.timedelta(days=15),
            "due_date": timezone.localdate() - timezone.timedelta(days=2),
            "progress_percentage": 100,
            "estimated_hours": Decimal("40.00"),
            "actual_hours": Decimal("38.50"),
        }
    )

    task2, _ = Task.objects.update_or_create(
        project=proj1,
        title="Admin Deliverables & Approvals Portal",
        defaults={
            "business": biz1,
            "assigned_vendor": vendor1,
            "created_by": admin1_user,
            "description": "Integrate two-stage review pipeline with live push notifications.",
            "priority": Task.Priority.URGENT,
            "status": Task.Status.SUBMITTED,
            "start_date": timezone.localdate() - timezone.timedelta(days=5),
            "due_date": timezone.localdate() + timezone.timedelta(days=3),
            "progress_percentage": 90,
            "estimated_hours": Decimal("30.00"),
            "actual_hours": Decimal("28.00"),
        }
    )

    TaskComment.objects.get_or_create(
        task=task2,
        author=vendor1_user,
        defaults={
            "author_role": "vendor",
            "message": "We have finalized the core API serializers and unit tests. Submitting v1.0 deliverable now.",
        }
    )

    # 7. Deliverables & Multi-Tier Approvals
    deliv1, _ = Deliverable.objects.update_or_create(
        project=proj1,
        task=task1,
        title="Checkout System & Payment Integration",
        defaults={
            "business": biz1,
            "vendor": vendor1,
            "submitted_by": vendor1_user,
            "description": "Complete production build of Stripe and PayPal checkout modules with full test coverage.",
            "version": "v1.0",
            "external_url": "https://github.com/apextech/checkout-module",
            "status": Deliverable.Status.CLIENT_APPROVED,
            "admin_notes": "Passed all security unit tests. Approved for staging deployment.",
            "client_notes": "Tested in sandbox environment. UI is super clean and fast. Approved!",
        }
    )
    DeliverableApproval.objects.get_or_create(
        deliverable=deliv1,
        reviewer=admin1_user,
        reviewer_role="admin",
        defaults={"action": "approve", "feedback": "Code quality verified and approved."}
    )
    DeliverableApproval.objects.get_or_create(
        deliverable=deliv1,
        reviewer=client1_user,
        reviewer_role="client",
        defaults={"action": "approve", "feedback": "Looks great on mobile and desktop!"}
    )

    deliv2, _ = Deliverable.objects.update_or_create(
        project=proj1,
        task=task2,
        title="Admin Review & Approval Architecture",
        defaults={
            "business": biz1,
            "vendor": vendor1,
            "submitted_by": vendor1_user,
            "description": "Real-time state machine for project deliverables and feedback logging.",
            "version": "v1.2",
            "external_url": "https://demo.apextech.io/approval-preview",
            "status": Deliverable.Status.CLIENT_REVIEW,
            "admin_notes": "Admin approval completed. Handing over to Eleanor for final client sign-off.",
        }
    )
    DeliverableApproval.objects.get_or_create(
        deliverable=deliv2,
        reviewer=admin1_user,
        reviewer_role="admin",
        defaults={"action": "approve", "feedback": "Approved by Admin. Ready for Client Review."}
    )

    # 8. Invoices & Payments for Business 1
    inv1, _ = Invoice.objects.update_or_create(
        business=biz1,
        invoice_number="INV-APX-001",
        defaults={
            "client": client1,
            "project": proj1,
            "issue_date": timezone.localdate() - timezone.timedelta(days=14),
            "due_date": timezone.localdate() - timezone.timedelta(days=2),
            "status": Invoice.Status.PAID,
            "subtotal": Decimal("20000.00"),
            "tax": Decimal("1600.00"),
            "total": Decimal("21600.00"),
            "paid_amount": Decimal("21600.00"),
            "balance_due": Decimal("0.00"),
            "notes": "Milestone 1: Architecture & Foundation completion.",
        }
    )
    InvoiceItem.objects.get_or_create(
        invoice=inv1,
        description="Milestone 1: E-Commerce Architecture & Checkout Build",
        defaults={"quantity": Decimal("1"), "unit_price": Decimal("20000.00"), "amount": Decimal("20000.00")}
    )

    pay1, _ = Payment.objects.update_or_create(
        business=biz1,
        invoice=inv1,
        defaults={
            "amount": Decimal("21600.00"),
            "method": Payment.Method.BANK,
            "status": Payment.Status.SUCCESS,
            "transaction_id": "TXN-BANK-8829104",
            "paid_at": timezone.now() - timezone.timedelta(days=3),
            "notes": "Wire transfer received in full.",
        }
    )
    Receipt.objects.get_or_create(
        business=biz1,
        payment=pay1,
        defaults={
            "invoice": inv1,
            "receipt_number": "REC-APX-001",
            "amount": Decimal("21600.00"),
            "issued_date": timezone.localdate() - timezone.timedelta(days=3),
            "notes": "Receipt issued for payment of INV-APX-001",
        }
    )

    inv2, _ = Invoice.objects.update_or_create(
        business=biz1,
        invoice_number="INV-APX-002",
        defaults={
            "client": client1,
            "project": proj1,
            "issue_date": timezone.localdate() - timezone.timedelta(days=3),
            "due_date": timezone.localdate() + timezone.timedelta(days=12),
            "status": Invoice.Status.SENT,
            "subtotal": Decimal("15000.00"),
            "tax": Decimal("1200.00"),
            "total": Decimal("16200.00"),
            "paid_amount": Decimal("0.00"),
            "balance_due": Decimal("16200.00"),
            "notes": "Milestone 2: Deliverables & Approvals Module deployment.",
        }
    )
    InvoiceItem.objects.get_or_create(
        invoice=inv2,
        description="Milestone 2: Multi-Tier Approvals & Notification System",
        defaults={"quantity": Decimal("1"), "unit_price": Decimal("15000.00"), "amount": Decimal("15000.00")}
    )

    # 9. Messages & Communication
    Message.objects.get_or_create(
        business=biz1,
        project=proj1,
        sender=vendor1_user,
        recipient=admin1_user,
        conversation_type=Message.ConversationType.DIRECT_ADMIN_VENDOR,
        defaults={
            "content": "Hi Marcus, the deliverable v1.2 is uploaded and ready for your review.",
            "is_read": True,
        }
    )
    Message.objects.get_or_create(
        business=biz1,
        project=proj1,
        sender=admin1_user,
        recipient=client1_user,
        conversation_type=Message.ConversationType.DIRECT_ADMIN_CLIENT,
        defaults={
            "content": "Hello Eleanor, Deliverable v1.2 has passed internal review and is now in your approvals queue.",
            "is_read": False,
        }
    )

    # 10. Audit Logs
    AuditLog.objects.get_or_create(
        business=biz1,
        actor=admin1_user,
        actor_role="ADMIN",
        action="CREATE_PROJECT",
        entity_type="Project",
        entity_id=str(proj1.id),
        defaults={
            "details": f"Created project '{proj1.title}' ({proj1.code}) with budget ${proj1.budget}",
            "ip_address": "127.0.0.1",
        }
    )
    AuditLog.objects.get_or_create(
        business=biz1,
        actor=vendor1_user,
        actor_role="VENDOR",
        action="SUBMIT_DELIVERABLE",
        entity_type="Deliverable",
        entity_id=str(deliv2.id),
        defaults={
            "details": f"Submitted deliverable '{deliv2.title}' ({deliv2.version})",
            "ip_address": "127.0.0.1",
        }
    )

    # 11. Notifications
    Notification.objects.get_or_create(
        user=admin1_user,
        business=biz1,
        title="Deliverable Ready",
        defaults={
            "message": f"Vendor {vendor1.name} submitted deliverable for project {proj1.title}.",
            "type": "deliverable",
            "link": f"/admin/deliverables/{deliv2.id}",
            "is_read": True,
        }
    )
    Notification.objects.get_or_create(
        user=client1_user,
        business=biz1,
        title="Approval Request",
        defaults={
            "message": f"New deliverable '{deliv2.title}' requires your review.",
            "type": "approval",
            "link": f"/client/approvals/{deliv2.id}",
            "is_read": False,
        }
    )

    # 12. Business 2: Sterling Logistics & Media (For multi-tenancy testing!)
    admin2_user, _ = User.objects.get_or_create(
        username="sterling_admin",
        defaults={
            "email": "admin@sterling.io",
            "first_name": "Jonathan",
            "last_name": "Sterling",
            "is_staff": True,
            "is_superuser": False,
        }
    )
    admin2_user.set_password("Admin123!")
    admin2_user.save()

    UserProfile.objects.update_or_create(
        user=admin2_user,
        defaults={"role": UserProfile.Role.ADMIN, "phone": "+1 312 555 7800"}
    )

    biz2, _ = BusinessProfile.objects.update_or_create(
        owner=admin2_user,
        defaults={
            "business_name": "Sterling Logistics & Fleet",
            "legal_name": "Sterling Logistics LLC",
            "business_type": "Logistics & Supply Chain",
            "email": "ops@sterling.io",
            "city": "Chicago",
            "state": "Illinois",
            "country": "United States",
            "currency": "USD",
            "is_active": True,
            "status": "active",
        }
    )
    AppSettings.objects.get_or_create(business=biz2)
    Subscription.objects.update_or_create(
        business=biz2,
        defaults={
            "plan_name": "Professional Tier",
            "status": Subscription.Status.ACTIVE,
            "monthly_price": Decimal("89.00"),
            "max_projects": 25,
            "max_users": 10,
        }
    )
    print("[+] Business 2 ready: Sterling Logistics (Admin: admin@sterling.io / Admin123!)")

    print("\n[SUCCESS] Multi-Tenant Database Seeding Completed Successfully!")


if __name__ == "__main__":
    seed()
