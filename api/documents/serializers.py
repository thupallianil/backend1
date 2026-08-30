from rest_framework import serializers
from api.models import Document, Project, Task, Client, Vendor


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "business",
            "project",
            "project_title",
            "task",
            "client",
            "client_name",
            "vendor",
            "vendor_name",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_by_username",
            "title",
            "file",
            "file_type",
            "file_size",
            "access_level",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "uploaded_by", "created_at", "updated_at"]
