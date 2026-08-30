from rest_framework import serializers
from api.models import Task, TaskComment, Project, Vendor
from api.vendors.serializers import VendorSerializer


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = TaskComment
        fields = [
            "id",
            "task",
            "author",
            "author_name",
            "author_username",
            "author_role",
            "message",
            "attachment",
            "created_at",
        ]
        read_only_fields = ["id", "author", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source="project.title", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    assigned_vendor_name = serializers.CharField(source="assigned_vendor.name", read_only=True)
    assigned_vendor_company = serializers.CharField(source="assigned_vendor.company_name", read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)
    deliverables_count = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "project_title",
            "project_code",
            "business",
            "assigned_vendor",
            "assigned_vendor_name",
            "assigned_vendor_company",
            "created_by",
            "title",
            "description",
            "priority",
            "status",
            "start_date",
            "due_date",
            "progress_percentage",
            "estimated_hours",
            "actual_hours",
            "comments",
            "deliverables_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "created_by", "created_at", "updated_at"]

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, "copy") else dict(data)
        for field in ["start_date", "due_date", "assigned_vendor"]:
            if field in data_copy and (data_copy[field] == "" or data_copy[field] is None):
                data_copy[field] = None
        if "estimated_hours" in data_copy and (data_copy["estimated_hours"] == "" or data_copy["estimated_hours"] is None):
            data_copy["estimated_hours"] = 0
        if "actual_hours" in data_copy and (data_copy["actual_hours"] == "" or data_copy["actual_hours"] is None):
            data_copy["actual_hours"] = 0
        return super().to_internal_value(data_copy)

    def get_deliverables_count(self, obj):
        return obj.deliverables.count()
