from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from api.models import Deliverable, DeliverableApproval, Project, Task, Vendor
from api.tenant_helpers import resolve_user_context, get_request_business
from api.utils_events import log_audit_event, send_system_notification
from .serializers import DeliverableSerializer, DeliverableApprovalSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def deliverable_list_create(request):
    role, user_biz, entity = resolve_user_context(request.user)

    if request.method == "GET":
        qs = Deliverable.objects.all()
        if role == "SUPER_ADMIN":
            biz_id = request.query_params.get("business_id")
            if biz_id:
                qs = qs.filter(business_id=biz_id)
        elif role == "ADMIN":
            if not user_biz:
                return Response([], status=status.HTTP_200_OK)
            qs = qs.filter(business=user_biz)
        elif role == "VENDOR":
            if not entity:
                return Response([], status=status.HTTP_200_OK)
            qs = qs.filter(vendor=entity)
        elif role == "CLIENT":
            if not entity:
                return Response([], status=status.HTTP_200_OK)
            # Clients see deliverables for their projects
            qs = qs.filter(project__client=entity)
        else:
            return Response([], status=status.HTTP_200_OK)

        project_id = request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        status_filter = request.query_params.get("status")
        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        serializer = DeliverableSerializer(qs.order_by("-created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        project_id = request.data.get("project")
        if not project_id:
            return Response({"error": "project is required"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(Project, pk=project_id)
        business = project.business

        # Determine Vendor
        if role == "VENDOR":
            vendor = entity
            if not vendor:
                return Response({"error": "No vendor profile linked"}, status=status.HTTP_400_BAD_REQUEST)
        elif role in ["ADMIN", "SUPER_ADMIN"]:
            vendor_id = request.data.get("vendor")
            if vendor_id:
                vendor = get_object_or_404(Vendor, pk=vendor_id, business=business)
            else:
                vendor = project.assigned_vendors.first()
                if not vendor:
                    vendor = Vendor.objects.filter(business=business).first()
        else:
            return Response({"error": "Clients cannot submit deliverables"}, status=status.HTTP_403_FORBIDDEN)

        task_id = request.data.get("task")
        task = Task.objects.filter(id=task_id, project=project).first() if task_id else None

        serializer = DeliverableSerializer(data=request.data)
        if serializer.is_valid():
            deliverable = serializer.save(
                project=project,
                business=business,
                vendor=vendor,
                task=task,
                submitted_by=request.user,
                status=Deliverable.Status.SUBMITTED
            )

            # Update task status if linked
            if task and task.status != "completed":
                task.status = "submitted"
                task.save(update_fields=["status"])

            # Notify Admin
            if business.owner:
                send_system_notification(
                    user=business.owner,
                    business=business,
                    title="New Deliverable Submitted",
                    message=f"Vendor {vendor.name} submitted deliverable '{deliverable.title}' on project '{project.title}'.",
                    notif_type="deliverable_submitted",
                    link=f"/admin/deliverables/{deliverable.id}"
                )

            log_audit_event(
                action="SUBMIT_DELIVERABLE",
                entity_type="Deliverable",
                entity_id=deliverable.id,
                business=business,
                actor=request.user,
                actor_role=role,
                details=f"Submitted deliverable '{deliverable.title}' ({deliverable.version}) for project '{project.title}'",
                request=request
            )

            return Response(DeliverableSerializer(deliverable).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def deliverable_detail(request, pk):
    role, user_biz, entity = resolve_user_context(request.user)
    deliverable = get_object_or_404(Deliverable, pk=pk)

    # Tenant and Resource auth
    if role == "ADMIN" and deliverable.business != user_biz:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "VENDOR" and deliverable.vendor != entity:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "CLIENT" and deliverable.project.client != entity:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response(DeliverableSerializer(deliverable).data, status=status.HTTP_200_OK)

    elif request.method in ["PUT", "PATCH"]:
        if role not in ["ADMIN", "VENDOR", "SUPER_ADMIN"]:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        serializer = DeliverableSerializer(deliverable, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            log_audit_event(
                action="UPDATE_DELIVERABLE",
                entity_type="Deliverable",
                entity_id=updated.id,
                business=updated.business,
                actor=request.user,
                actor_role=role,
                details=f"Updated deliverable '{updated.title}'",
                request=request
            )
            return Response(DeliverableSerializer(updated).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        if role not in ["ADMIN", "SUPER_ADMIN"]:
            return Response({"error": "Only admins can delete deliverables"}, status=status.HTTP_403_FORBIDDEN)

        title = deliverable.title
        did = deliverable.id
        biz = deliverable.business
        deliverable.delete()

        log_audit_event(
            action="DELETE_DELIVERABLE",
            entity_type="Deliverable",
            entity_id=did,
            business=biz,
            actor=request.user,
            actor_role=role,
            details=f"Deleted deliverable '{title}'",
            request=request
        )
        return Response({"message": "Deliverable deleted"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deliverable_admin_review(request, pk):
    """
    Admin reviews vendor deliverable:
    - approve: moves status to client_review, notifies client and vendor.
    - reject: moves status to revision_required, notifies vendor.
    """
    role, user_biz, _ = resolve_user_context(request.user)
    if role not in ["ADMIN", "SUPER_ADMIN"]:
        return Response({"error": "Only admins can perform admin review"}, status=status.HTTP_403_FORBIDDEN)

    deliverable = get_object_or_404(Deliverable, pk=pk)
    if role == "ADMIN" and deliverable.business != user_biz:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    action = request.data.get("action")  # "approve" or "reject"
    feedback = request.data.get("feedback", "").strip()

    if action not in ["approve", "reject"]:
        return Response({"error": "action must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)

    approval = DeliverableApproval.objects.create(
        deliverable=deliverable,
        reviewer=request.user,
        reviewer_role="admin",
        action="approve" if action == "approve" else "reject",
        feedback=feedback
    )

    if action == "approve":
        deliverable.status = Deliverable.Status.CLIENT_REVIEW
        deliverable.admin_notes = feedback
        deliverable.save(update_fields=["status", "admin_notes"])

        # Notify Vendor
        if deliverable.vendor and deliverable.vendor.user:
            send_system_notification(
                user=deliverable.vendor.user,
                business=deliverable.business,
                title="Deliverable Approved by Admin",
                message=f"Your deliverable '{deliverable.title}' was approved by Admin and sent for Client Review.",
                notif_type="deliverable_approved_admin",
                link=f"/vendor/deliverables/{deliverable.id}"
            )

        # Notify Client
        if deliverable.project.client and deliverable.project.client.user:
            send_system_notification(
                user=deliverable.project.client.user,
                business=deliverable.business,
                title="Deliverable Ready for Your Review",
                message=f"Deliverable '{deliverable.title}' on project '{deliverable.project.title}' is ready for your review and approval.",
                notif_type="deliverable_client_review",
                link=f"/client/approvals/{deliverable.id}"
            )
    else:
        deliverable.status = Deliverable.Status.REVISION_REQUIRED
        deliverable.admin_notes = feedback
        deliverable.save(update_fields=["status", "admin_notes"])

        if deliverable.task:
            deliverable.task.status = "revision_required"
            deliverable.task.save(update_fields=["status"])

        # Notify Vendor
        if deliverable.vendor and deliverable.vendor.user:
            send_system_notification(
                user=deliverable.vendor.user,
                business=deliverable.business,
                title="Revision Required on Deliverable",
                message=f"Admin requested revisions on '{deliverable.title}': {feedback or 'Please review notes'}",
                notif_type="deliverable_rejected",
                link=f"/vendor/deliverables/{deliverable.id}"
            )

    log_audit_event(
        action=f"ADMIN_REVIEW_{action.upper()}",
        entity_type="Deliverable",
        entity_id=deliverable.id,
        business=deliverable.business,
        actor=request.user,
        actor_role=role,
        details=f"Admin {action}ed deliverable '{deliverable.title}'. Feedback: {feedback}",
        request=request
    )

    return Response(DeliverableSerializer(deliverable).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deliverable_client_review(request, pk):
    """
    Client reviews deliverable:
    - approve: moves status to client_approved / completed, completes task/project progress.
    - request_changes: moves status to client_changes_requested / revision_required.
    """
    role, user_biz, entity = resolve_user_context(request.user)
    deliverable = get_object_or_404(Deliverable, pk=pk)

    # Client check
    if role == "CLIENT" and deliverable.project.client != entity:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    elif role not in ["CLIENT", "ADMIN", "SUPER_ADMIN"]:
        return Response({"error": "Only client or admin can record client review"}, status=status.HTTP_403_FORBIDDEN)

    action = request.data.get("action")  # "approve" or "request_changes"
    feedback = request.data.get("feedback", "").strip()

    if action not in ["approve", "request_changes"]:
        return Response({"error": "action must be 'approve' or 'request_changes'"}, status=status.HTTP_400_BAD_REQUEST)

    approval = DeliverableApproval.objects.create(
        deliverable=deliverable,
        reviewer=request.user,
        reviewer_role="client",
        action="approve" if action == "approve" else "request_changes",
        feedback=feedback
    )

    if action == "approve":
        deliverable.status = Deliverable.Status.CLIENT_APPROVED
        deliverable.client_notes = feedback
        deliverable.save(update_fields=["status", "client_notes"])

        # Mark task completed if linked
        if deliverable.task:
            deliverable.task.status = "completed"
            deliverable.task.progress_percentage = 100
            deliverable.task.save(update_fields=["status", "progress_percentage"])

        # Update project progress
        project = deliverable.project
        total = project.tasks.count()
        if total > 0:
            done = project.tasks.filter(status="completed").count()
            project.progress_percentage = int((done / total) * 100)
            if done == total:
                project.status = "completed"
            project.save(update_fields=["progress_percentage", "status"])

        # Notify Admin
        if project.business and project.business.owner:
            send_system_notification(
                user=project.business.owner,
                business=project.business,
                title="Client Approved Deliverable 🎉",
                message=f"Client approved deliverable '{deliverable.title}' on project '{project.title}'.",
                notif_type="client_approved",
                link=f"/admin/deliverables/{deliverable.id}"
            )

        # Notify Vendor
        if deliverable.vendor and deliverable.vendor.user:
            send_system_notification(
                user=deliverable.vendor.user,
                business=deliverable.business,
                title="Client Approved Your Deliverable 🎉",
                message=f"Great job! Client approved deliverable '{deliverable.title}'.",
                notif_type="client_approved",
                link=f"/vendor/deliverables/{deliverable.id}"
            )
    else:
        deliverable.status = Deliverable.Status.CLIENT_CHANGES_REQUESTED
        deliverable.client_notes = feedback
        deliverable.save(update_fields=["status", "client_notes"])

        if deliverable.task:
            deliverable.task.status = "revision_required"
            deliverable.task.save(update_fields=["status"])

        # Notify Admin
        if deliverable.business.owner:
            send_system_notification(
                user=deliverable.business.owner,
                business=deliverable.business,
                title="Client Requested Changes",
                message=f"Client requested changes on '{deliverable.title}': {feedback}",
                notif_type="client_changes_requested",
                link=f"/admin/deliverables/{deliverable.id}"
            )

        # Notify Vendor
        if deliverable.vendor and deliverable.vendor.user:
            send_system_notification(
                user=deliverable.vendor.user,
                business=deliverable.business,
                title="Client Requested Changes on Deliverable",
                message=f"Client requested modifications: {feedback}",
                notif_type="client_changes_requested",
                link=f"/vendor/deliverables/{deliverable.id}"
            )

    log_audit_event(
        action=f"CLIENT_REVIEW_{action.upper()}",
        entity_type="Deliverable",
        entity_id=deliverable.id,
        business=deliverable.business,
        actor=request.user,
        actor_role=role,
        details=f"Client {action}ed deliverable '{deliverable.title}'. Feedback: {feedback}",
        request=request
    )

    return Response(DeliverableSerializer(deliverable).data, status=status.HTTP_200_OK)
