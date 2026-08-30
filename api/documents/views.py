from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from api.models import Document, Project, Client, Vendor
from api.tenant_helpers import resolve_user_context, get_request_business
from api.utils_events import log_audit_event
from .serializers import DocumentSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def document_list_create(request):
    role, user_biz, entity = resolve_user_context(request.user)

    if request.method == "GET":
        qs = Document.objects.all()
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
            # Vendors see public_tenant docs, docs specifically tagged to them, or project_members docs on assigned projects
            qs = qs.filter(
                Q(vendor=entity) |
                Q(access_level="public_tenant") |
                Q(access_level="project_members", project__members__vendor=entity)
            ).distinct()
        elif role == "CLIENT":
            if not entity:
                return Response([], status=status.HTTP_200_OK)
            # Clients see docs tagged to them or client_visible on their projects
            qs = qs.filter(
                Q(client=entity) |
                Q(access_level="client_visible", project__client=entity)
            ).distinct()
        else:
            return Response([], status=status.HTTP_200_OK)

        project_id = request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(file_type__icontains=search))

        serializer = DocumentSerializer(qs.order_by("-created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        business = user_biz or get_request_business(request)
        if not business:
            return Response({"error": "No associated business found"}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES.get("file")
        title = request.data.get("title") or (file_obj.name if file_obj else "Document")

        file_type = ""
        file_size = ""
        if file_obj:
            file_type = file_obj.content_type or file_obj.name.split(".")[-1]
            size_kb = file_obj.size / 1024
            file_size = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{(size_kb/1024):.1f} MB"

        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            doc = serializer.save(
                business=business,
                uploaded_by=request.user,
                title=title,
                file_type=file_type,
                file_size=file_size
            )

            log_audit_event(
                action="UPLOAD_DOCUMENT",
                entity_type="Document",
                entity_id=doc.id,
                business=business,
                actor=request.user,
                actor_role=role,
                details=f"Uploaded document '{doc.title}' ({doc.file_size})",
                request=request
            )

            return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def document_detail(request, pk):
    role, user_biz, entity = resolve_user_context(request.user)
    doc = get_object_or_404(Document, pk=pk)

    if role == "ADMIN" and doc.business != user_biz:
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response(DocumentSerializer(doc).data, status=status.HTTP_200_OK)

    elif request.method == "DELETE":
        if role not in ["ADMIN", "SUPER_ADMIN"] and doc.uploaded_by != request.user:
            return Response({"error": "Unauthorized to delete document"}, status=status.HTTP_403_FORBIDDEN)

        title = doc.title
        did = doc.id
        biz = doc.business
        doc.delete()

        log_audit_event(
            action="DELETE_DOCUMENT",
            entity_type="Document",
            entity_id=did,
            business=biz,
            actor=request.user,
            actor_role=role,
            details=f"Deleted document '{title}'",
            request=request
        )

        return Response({"message": "Document deleted"}, status=status.HTTP_200_OK)
