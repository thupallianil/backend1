from rest_framework import serializers
from api.models import Project, ProjectMember, Vendor, Client
from api.clients.serializers import ClientSerializer
from api.vendors.serializers import VendorSerializer


class ProjectMemberSerializer(serializers.ModelSerializer):
    vendor_details = VendorSerializer(source="vendor", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    vendor_company = serializers.CharField(source="vendor.company_name", read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            "id",
            "project",
            "vendor",
            "vendor_name",
            "vendor_company",
            "vendor_details",
            "role",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at"]


class ProjectSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_company = serializers.CharField(source="client.company_name", read_only=True)
    client_email = serializers.CharField(source="client.email", read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    tasks_count = serializers.SerializerMethodField()
    completed_tasks_count = serializers.SerializerMethodField()
    deliverables_count = serializers.SerializerMethodField()
    pending_approvals_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "business",
            "client",
            "client_name",
            "client_company",
            "client_email",
            "created_by",
            "title",
            "code",
            "description",
            "status",
            "priority",
            "budget",
            "start_date",
            "end_date",
            "progress_percentage",
            "members",
            "tasks_count",
            "completed_tasks_count",
            "deliverables_count",
            "pending_approvals_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "business", "created_by", "created_at", "updated_at"]

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, "copy") else dict(data)
        for field in ["start_date", "end_date", "client"]:
            if field in data_copy and (data_copy[field] == "" or data_copy[field] is None):
                data_copy[field] = None
        if "budget" in data_copy and (data_copy["budget"] == "" or data_copy["budget"] is None):
            data_copy["budget"] = 0
        return super().to_internal_value(data_copy)

    def get_tasks_count(self, obj):
        return obj.tasks.count()

    def get_completed_tasks_count(self, obj):
        return obj.tasks.filter(status="completed").count()

    def get_deliverables_count(self, obj):
        return obj.deliverables.count()

    def get_pending_approvals_count(self, obj):
        return obj.deliverables.filter(status__in=["submitted", "admin_review", "client_review"]).count()
