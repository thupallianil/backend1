from rest_framework import serializers
from api.models import Deliverable, DeliverableApproval, Task, Project, Vendor


class DeliverableApprovalSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True)

    class Meta:
        model = DeliverableApproval
        fields = [
            "id",
            "deliverable",
            "reviewer",
            "reviewer_name",
            "reviewer_username",
            "reviewer_role",
            "action",
            "feedback",
            "created_at",
        ]
        read_only_fields = ["id", "reviewer", "created_at"]


class DeliverableSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source="project.title", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    client_name = serializers.CharField(source="project.client.name", read_only=True)
    client_company = serializers.CharField(source="project.client.company_name", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    vendor_company = serializers.CharField(source="vendor.company_name", read_only=True)
    approvals = DeliverableApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = Deliverable
        fields = [
            "id",
            "task",
            "task_title",
            "project",
            "project_title",
            "project_code",
            "business",
            "client_name",
            "client_company",
            "vendor",
            "vendor_name",
            "vendor_company",
            "submitted_by",
            "title",
            "description",
            "version",
            "file_attachment",
            "external_url",
            "status",
            "admin_notes",
            "client_notes",
            "approvals",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "vendor", "submitted_by", "created_at", "updated_at"]
