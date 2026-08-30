from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from api.models import Task, TaskComment, Project, Vendor
from api.tenant_helpers import resolve_user_context, get_request_business
from api.utils_events import log_audit_event, send_system_notification
from .serializers import TaskSerializer, TaskCommentSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_list_create(request):
    role, user_biz, entity = resolve_user_context(request.user)

    if request.method == "GET":
        qs = Task.objects.all()
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
            qs = qs.filter(Q(assigned_vendor=entity) | Q(project__members__vendor=entity)).distinct()
        elif role == "CLIENT":
            if not entity:
                return Response([], status=status.HTTP_200_OK)
            qs = qs.filter(project__client=entity)
        else:
            return Response([], status=status.HTTP_200_OK)

        project_id = request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            qs = qs.filter(assigned_vendor_id=vendor_id)

        status_filter = request.query_params.get("status")
        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)

        priority = request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        serializer = TaskSerializer(qs.order_by("due_date", "-created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        if role not in ["ADMIN", "SUPER_ADMIN"]:
            return Response({"error": "Only admins can create tasks"}, status=status.HTTP_403_FORBIDDEN)

        project_id = request.data.get("project")
        if not project_id:
            return Response({"error": "project is required"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(Project, pk=project_id)
        business = project.business

        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save(
                project=project,
                business=business,
                created_by=request.user
            )

            # Recalculate project progress
            total_tasks = project.tasks.count()
            if total_tasks > 0:
                completed = project.tasks.filter(status="completed").count()
                project.progress_percentage = int((completed / total_tasks) * 100)
                project.save(update_fields=["progress_percentage"])

            # Notify vendor
            if task.assigned_vendor and task.assigned_vendor.user:
                send_system_notification(
                    user=task.assigned_vendor.user,
                    business=business,
                    title="New Task Assigned",
                    message=f"You have been assigned task: '{task.title}' on project '{project.title}'.",
                    notif_type="task_assigned",
                    link=f"/vendor/tasks/{task.id}"
                )

            log_audit_event(
                action="CREATE_TASK",
                entity_type="Task",
                entity_id=task.id,
                business=business,
                actor=request.user,
                actor_role=role,
                details=f"Created task '{task.title}' for project '{project.title}'",
                request=request
            )

            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def task_detail(request, pk):
    role, user_biz, entity = resolve_user_context(request.user)
    task = get_object_or_404(Task, pk=pk)

    # Authorization
    if role == "ADMIN" and task.business != user_biz:
        return Response({"error": "Unauthorized access to task"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "VENDOR" and task.assigned_vendor != entity and not task.project.members.filter(vendor=entity).exists():
        return Response({"error": "Unauthorized access to task"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "CLIENT" and task.project.client != entity:
        return Response({"error": "Unauthorized access to task"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    elif request.method in ["PUT", "PATCH"]:
        partial = request.method == "PATCH"

        # Vendor limited update vs Admin full update
        if role == "VENDOR":
            allowed_fields = ["status", "progress_percentage", "actual_hours"]
            for key in list(request.data.keys()):
                if key not in allowed_fields:
                    request.data.pop(key, None)

        serializer = TaskSerializer(task, data=request.data, partial=partial)
        if serializer.is_valid():
            updated = serializer.save()

            # Dynamic recalculation of project progress
            project = updated.project
            total_tasks = project.tasks.count()
            if total_tasks > 0:
                completed = project.tasks.filter(status="completed").count()
                project.progress_percentage = int((completed / total_tasks) * 100)
                if completed == total_tasks and total_tasks > 0 and project.status != "completed":
                    # Keep under_review or completed
                    pass
                project.save(update_fields=["progress_percentage"])

            # If vendor updated status to submitted or completed -> notify Admin
            if role == "VENDOR" and "status" in request.data:
                if project.business and project.business.owner:
                    send_system_notification(
                        user=project.business.owner,
                        business=project.business,
                        title="Task Progress Updated",
                        message=f"Vendor {entity.name} updated task '{updated.title}' to {updated.status} ({updated.progress_percentage}%).",
                        notif_type="task_progress",
                        link=f"/admin/tasks/{updated.id}"
                    )

            log_audit_event(
                action="UPDATE_TASK",
                entity_type="Task",
                entity_id=updated.id,
                business=updated.business,
                actor=request.user,
                actor_role=role,
                details=f"Updated task '{updated.title}' status={updated.status}, progress={updated.progress_percentage}%",
                request=request
            )

            return Response(TaskSerializer(updated).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        if role not in ["ADMIN", "SUPER_ADMIN"]:
            return Response({"error": "Only admins can delete tasks"}, status=status.HTTP_403_FORBIDDEN)

        title = task.title
        task_id = task.id
        biz = task.business
        task.delete()

        log_audit_event(
            action="DELETE_TASK",
            entity_type="Task",
            entity_id=task_id,
            business=biz,
            actor=request.user,
            actor_role=role,
            details=f"Deleted task '{title}'",
            request=request
        )

        return Response({"message": "Task deleted"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def task_add_comment(request, pk):
    role, user_biz, entity = resolve_user_context(request.user)
    task = get_object_or_404(Task, pk=pk)

    # Permission check
    if role == "ADMIN" and task.business != user_biz:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
    elif role == "VENDOR" and task.assigned_vendor != entity and not task.project.members.filter(vendor=entity).exists():
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    message = request.data.get("message")
    if not message:
        return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

    attachment = request.FILES.get("attachment")

    comment = TaskComment.objects.create(
        task=task,
        author=request.user,
        author_role=role.lower(),
        message=message,
        attachment=attachment
    )

    # Notify recipient
    if role == "ADMIN" and task.assigned_vendor and task.assigned_vendor.user:
        send_system_notification(
            user=task.assigned_vendor.user,
            business=task.business,
            title="New Comment on Task",
            message=f"Admin commented on task '{task.title}': {message[:80]}",
            notif_type="task_comment",
            link=f"/vendor/tasks/{task.id}"
        )
    elif role == "VENDOR" and task.business and task.business.owner:
        send_system_notification(
            user=task.business.owner,
            business=task.business,
            title="Vendor Comment on Task",
            message=f"Vendor commented on task '{task.title}': {message[:80]}",
            notif_type="task_comment",
            link=f"/admin/tasks/{task.id}"
        )

    return Response(TaskCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
