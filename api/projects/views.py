from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from django.utils import timezone
import uuid

from api.models import Project, ProjectMember, Vendor, Client, BusinessProfile
from api.tenant_helpers import resolve_user_context, get_request_business
from api.utils_events import log_audit_event, send_system_notification
from .serializers import ProjectSerializer, ProjectMemberSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def project_list_create(request):
    role, user_biz, entity = resolve_user_context(request.user)

    if request.method == "GET":
        qs = Project.objects.all()
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
            qs = qs.filter(members__vendor=entity).distinct()
        elif role == "CLIENT":
            if not entity:
                return Response([], status=status.HTTP_200_OK)
            qs = qs.filter(client=entity)
        else:
            return Response([], status=status.HTTP_200_OK)

        # Filters
        status_filter = request.query_params.get("status")
        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(code__icontains=search) | Q(description__icontains=search))

        serializer = ProjectSerializer(qs.order_by("-created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        if role not in ["ADMIN", "SUPER_ADMIN"]:
            return Response({"error": "Only admins can create projects"}, status=status.HTTP_403_FORBIDDEN)

        business = user_biz or get_request_business(request)
        if not business:
            return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

        from django.db import transaction
        from api.models import Subscription

        with transaction.atomic():
            # Lock subscription record for atomic quota check
            subscription, _ = Subscription.objects.select_for_update().get_or_create(
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

            current_projects_count = Project.objects.filter(business=business).count()

            # 1. FREE_TRIAL ENFORCEMENT
            if subscription.plan_name == Subscription.Plan.FREE_TRIAL:
                if current_projects_count >= subscription.trial_limit:
                    if subscription.status != Subscription.Status.TRIAL_EXHAUSTED:
                        subscription.status = Subscription.Status.TRIAL_EXHAUSTED
                        subscription.trial_used = current_projects_count
                        subscription.save(update_fields=["status", "trial_used"])

                    log_audit_event(
                        action="PROJECT_CREATION_BLOCKED",
                        entity_type="Subscription",
                        entity_id=subscription.id,
                        business=business,
                        actor=request.user,
                        actor_role=role,
                        details=f"Project creation blocked: Free trial project quota ({subscription.trial_limit}) exhausted.",
                        request=request
                    )

                    if business.owner:
                        send_system_notification(
                            user=business.owner,
                            business=business,
                            title="Free Trial Completed",
                            message="Your 5-project free trial has ended. Upgrade your subscription to continue creating projects.",
                            notif_type="trial_exhausted",
                            link="/admin/subscription"
                        )

                    return Response({
                        "code": "TRIAL_EXHAUSTED",
                        "message": "Your free trial includes 5 projects. Please upgrade your subscription to create more projects.",
                        "trial_used": current_projects_count,
                        "trial_limit": subscription.trial_limit,
                    }, status=status.HTTP_403_FORBIDDEN)

            # 2. PAID PLAN ENFORCEMENT
            else:
                if subscription.status != Subscription.Status.ACTIVE:
                    return Response({
                        "code": "SUBSCRIPTION_INACTIVE",
                        "message": f"Your subscription status is {subscription.status}. Please activate or renew your plan.",
                    }, status=status.HTTP_403_FORBIDDEN)

                if current_projects_count >= subscription.max_projects:
                    log_audit_event(
                        action="PROJECT_CREATION_BLOCKED",
                        entity_type="Subscription",
                        entity_id=subscription.id,
                        business=business,
                        actor=request.user,
                        actor_role=role,
                        details=f"Project creation blocked: Paid plan '{subscription.plan_name}' project limit ({subscription.max_projects}) reached.",
                        request=request
                    )

                    return Response({
                        "code": "PROJECT_LIMIT_REACHED",
                        "message": "Your current subscription project limit has been reached. Please upgrade your plan.",
                        "current_count": current_projects_count,
                        "max_projects": subscription.max_projects,
                    }, status=status.HTTP_403_FORBIDDEN)

            data = request.data.copy()
            code = data.get("code") or f"PRJ-{uuid.uuid4().hex[:6].upper()}"

            serializer = ProjectSerializer(data=data)
            if serializer.is_valid():
                project = serializer.save(
                    business=business,
                    created_by=request.user,
                    code=code
                )

                # Update subscription counters and trial alerts
                new_count = current_projects_count + 1
                if subscription.plan_name == Subscription.Plan.FREE_TRIAL:
                    subscription.trial_used = new_count
                    if new_count >= subscription.trial_limit:
                        subscription.status = Subscription.Status.TRIAL_EXHAUSTED
                        subscription.trial_ended_at = timezone.now()
                        if business.owner:
                            send_system_notification(
                                user=business.owner,
                                business=business,
                                title="Free Trial Completed",
                                message="You have created 5 of 5 free trial projects. Your free trial has ended. Upgrade your subscription to continue creating projects.",
                                notif_type="trial_exhausted",
                                link="/admin/subscription"
                            )
                        log_audit_event(
                            action="TRIAL_LIMIT_REACHED",
                            entity_type="Subscription",
                            entity_id=subscription.id,
                            business=business,
                            actor=request.user,
                            actor_role=role,
                            details="Business consumed all 5 free trial projects.",
                            request=request
                        )
                    elif new_count == 4:
                        if business.owner:
                            send_system_notification(
                                user=business.owner,
                                business=business,
                                title="Free Trial Project Alert",
                                message="You have created 4 of 5 free trial projects. One free project remains.",
                                notif_type="trial_warning",
                                link="/admin/subscription"
                            )
                    subscription.save()

                # Optional vendor assignment at creation
                vendor_ids = request.data.get("vendor_ids", [])
                if isinstance(vendor_ids, list):
                    for vid in vendor_ids:
                        vendor = Vendor.objects.filter(id=vid, business=business).first()
                        if vendor:
                            ProjectMember.objects.get_or_create(project=project, vendor=vendor)
                            if vendor.user:
                                send_system_notification(
                                    user=vendor.user,
                                    business=business,
                                    title="Assigned to New Project",
                                    message=f"You have been assigned to project: {project.title}",
                                    notif_type="project_assignment",
                                    link=f"/vendor/projects/{project.id}"
                                )

                # Notify Client if linked
                if project.client and project.client.user:
                    send_system_notification(
                        user=project.client.user,
                        business=business,
                        title="New Project Started",
                        message=f"A new project '{project.title}' has been initialized for you.",
                        notif_type="project_created",
                        link=f"/client/projects/{project.id}"
                    )

                log_audit_event(
                    action="CREATE_PROJECT",
                    entity_type="Project",
                    entity_id=project.id,
                    business=business,
                    actor=request.user,
                    actor_role=role,
                    details=f"Created project '{project.title}' ({project.code}) [Plan: {subscription.plan_name}]",
                    request=request
                )

                return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def project_detail(request, pk):
    role, user_biz, entity = resolve_user_context(request.user)
    project = get_object_or_404(Project, pk=pk)

    # Tenant & Resource Authorization check
    if role == "ADMIN" and project.business != user_biz:
        return Response({"error": "Unauthorized access to tenant project"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "VENDOR" and not project.members.filter(vendor=entity).exists():
        return Response({"error": "Unauthorized access to project"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "CLIENT" and project.client != entity:
        return Response({"error": "Unauthorized access to project"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        serializer = ProjectSerializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ["PUT", "PATCH"]:
        if role not in ["ADMIN", "SUPER_ADMIN"]:
            return Response({"error": "Only admins can edit projects"}, status=status.HTTP_403_FORBIDDEN)

        partial = request.method == "PATCH"
        serializer = ProjectSerializer(project, data=request.data, partial=partial)
        if serializer.is_valid():
            updated = serializer.save()
            log_audit_event(
                action="UPDATE_PROJECT",
                entity_type="Project",
                entity_id=updated.id,
                business=updated.business,
                actor=request.user,
                actor_role=role,
                details=f"Updated project '{updated.title}'",
                request=request
            )
            return Response(ProjectSerializer(updated).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        if role not in ["ADMIN", "SUPER_ADMIN"]:
            return Response({"error": "Only admins can delete projects"}, status=status.HTTP_403_FORBIDDEN)

        project_title = project.title
        project_id = project.id
        biz = project.business
        project.delete()

        log_audit_event(
            action="DELETE_PROJECT",
            entity_type="Project",
            entity_id=project_id,
            business=biz,
            actor=request.user,
            actor_role=role,
            details=f"Deleted project '{project_title}'",
            request=request
        )
        return Response({"message": "Project deleted successfully"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def project_assign_vendor(request, pk):
    role, user_biz, _ = resolve_user_context(request.user)
    if role not in ["ADMIN", "SUPER_ADMIN"]:
        return Response({"error": "Only admins can assign vendors"}, status=status.HTTP_403_FORBIDDEN)

    project = get_object_or_404(Project, pk=pk)
    if role == "ADMIN" and project.business != user_biz:
        return Response({"error": "Unauthorized access to project"}, status=status.HTTP_403_FORBIDDEN)

    vendor_id = request.data.get("vendor_id")
    role_title = request.data.get("role", "Assigned Vendor")

    vendor = get_object_or_404(Vendor, pk=vendor_id, business=project.business)
    membership, created = ProjectMember.objects.get_or_create(
        project=project,
        vendor=vendor,
        defaults={"role": role_title}
    )
    if not created and role_title:
        membership.role = role_title
        membership.save()

    if vendor.user:
        send_system_notification(
            user=vendor.user,
            business=project.business,
            title="Assigned to Project",
            message=f"You have been assigned to project: {project.title}",
            notif_type="project_assignment",
            link=f"/vendor/projects/{project.id}"
        )

    log_audit_event(
        action="ASSIGN_VENDOR_PROJECT",
        entity_type="ProjectMember",
        entity_id=membership.id,
        business=project.business,
        actor=request.user,
        actor_role=role,
        details=f"Assigned vendor '{vendor.name}' to project '{project.title}'",
        request=request
    )

    return Response(ProjectMemberSerializer(membership).data, status=status.HTTP_201_CREATED)


@api_view(["DELETE", "POST"])
@permission_classes([IsAuthenticated])
def project_remove_vendor(request, pk, vendor_id):
    role, user_biz, _ = resolve_user_context(request.user)
    if role not in ["ADMIN", "SUPER_ADMIN"]:
        return Response({"error": "Only admins can remove vendors"}, status=status.HTTP_403_FORBIDDEN)

    project = get_object_or_404(Project, pk=pk)
    if role == "ADMIN" and project.business != user_biz:
        return Response({"error": "Unauthorized access to project"}, status=status.HTTP_403_FORBIDDEN)

    membership = ProjectMember.objects.filter(project=project, vendor_id=vendor_id).first()
    if membership:
        membership.delete()
        log_audit_event(
            action="REMOVE_VENDOR_PROJECT",
            entity_type="ProjectMember",
            entity_id=vendor_id,
            business=project.business,
            actor=request.user,
            actor_role=role,
            details=f"Removed vendor #{vendor_id} from project '{project.title}'",
            request=request
        )

    return Response({"message": "Vendor removed from project"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_stats(request):
    role, user_biz, entity = resolve_user_context(request.user)
    qs = Project.objects.all()

    if role == "ADMIN":
        if not user_biz:
            return Response({}, status=status.HTTP_200_OK)
        qs = qs.filter(business=user_biz)
    elif role == "VENDOR":
        if not entity:
            return Response({}, status=status.HTTP_200_OK)
        qs = qs.filter(members__vendor=entity).distinct()
    elif role == "CLIENT":
        if not entity:
            return Response({}, status=status.HTTP_200_OK)
        qs = qs.filter(client=entity)

    total_projects = qs.count()
    active_projects = qs.filter(status__in=["active", "in_progress"]).count()
    completed_projects = qs.filter(status="completed").count()
    pending_projects = qs.filter(status__in=["pending", "draft"]).count()
    under_review = qs.filter(status__in=["under_review", "client_review"]).count()
    total_budget = qs.aggregate(sum_budget=Sum("budget"))["sum_budget"] or 0

    return Response({
        "total": total_projects,
        "active": active_projects,
        "completed": completed_projects,
        "pending": pending_projects,
        "under_review": under_review,
        "total_budget": float(total_budget),
    }, status=status.HTTP_200_OK)
