from rest_framework import serializers
from api.models import Subscription, BusinessProfile, Project


class SubscriptionSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.business_name", read_only=True)
    business_email = serializers.CharField(source="business.email", read_only=True)
    owner_username = serializers.CharField(source="business.owner.username", read_only=True)
    owner_email = serializers.CharField(source="business.owner.email", read_only=True)

    projects_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    is_trial = serializers.SerializerMethodField()
    trial_remaining = serializers.SerializerMethodField()
    upgrade_required = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "business",
            "business_name",
            "business_email",
            "owner_username",
            "owner_email",
            "plan_name",
            "status",
            "monthly_price",
            "billing_cycle",
            "max_projects",
            "max_users",
            "trial_limit",
            "trial_used",
            "trial_started_at",
            "trial_ended_at",
            "valid_until",
            "projects_count",
            "users_count",
            "is_trial",
            "trial_remaining",
            "upgrade_required",
            "created_at",
            "updated_at",
        ]

    def get_projects_count(self, obj):
        if hasattr(obj, "business") and obj.business:
            return Project.objects.filter(business=obj.business).count()
        return 0

    def get_users_count(self, obj):
        if hasattr(obj, "business") and obj.business:
            b = obj.business
            return b.clients.count() + b.vendors.count() + 1
        return 0

    def get_is_trial(self, obj):
        return obj.plan_name == Subscription.Plan.FREE_TRIAL or "trial" in obj.status.lower()

    def get_trial_remaining(self, obj):
        if obj.plan_name == Subscription.Plan.FREE_TRIAL:
            projects_cnt = self.get_projects_count(obj)
            return max(0, obj.trial_limit - projects_cnt)
        return 0

    def get_upgrade_required(self, obj):
        if obj.plan_name == Subscription.Plan.FREE_TRIAL:
            return self.get_projects_count(obj) >= obj.trial_limit or obj.status == Subscription.Status.TRIAL_EXHAUSTED
        if obj.status in [Subscription.Status.PAST_DUE, Subscription.Status.EXPIRED]:
            return True
        return self.get_projects_count(obj) >= obj.max_projects
