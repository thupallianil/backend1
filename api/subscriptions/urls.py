from django.urls import path
from .views import (
    subscription_list_create,
    subscription_detail,
    current_subscription,
    subscription_usage,
    available_plans,
    upgrade_subscription,
    verify_subscription_payment,
)

urlpatterns = [
    path("", subscription_list_create, name="subscription-list-create"),
    path("current/", current_subscription, name="subscription-current"),
    path("usage/", subscription_usage, name="subscription-usage"),
    path("plans/", available_plans, name="subscription-plans"),
    path("upgrade/", upgrade_subscription, name="subscription-upgrade"),
    path("payment/verify/", verify_subscription_payment, name="subscription-payment-verify"),
    path("<int:pk>/", subscription_detail, name="subscription-detail"),
]
