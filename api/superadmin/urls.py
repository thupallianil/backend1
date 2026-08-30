from django.urls import path
from . import views

urlpatterns = [
    path("stats/", views.superadmin_stats, name="superadmin_stats"),
    path("dashboard/", views.superadmin_stats, name="superadmin_dashboard"),
    path("tenants/", views.superadmin_tenants, name="superadmin_tenants"),
    path("tenants/<int:pk>/toggle/", views.superadmin_toggle_tenant, name="superadmin_toggle_tenant"),
    path("users/", views.superadmin_users, name="superadmin_users"),
    path("subscriptions/", views.superadmin_subscriptions, name="superadmin_subscriptions"),
    path("revenue/", views.superadmin_revenue, name="superadmin_revenue"),
    path("settings/", views.superadmin_settings, name="superadmin_settings"),
    path("settings/test-email/", views.superadmin_test_email, name="superadmin_test_email"),
    path("impersonate/", views.superadmin_impersonate, name="superadmin_impersonate"),
    path("impersonate/<int:admin_id>/", views.superadmin_impersonate, name="superadmin_impersonate_by_id"),
    path("impersonate/exit/", views.superadmin_impersonate_exit, name="superadmin_impersonate_exit"),
    path("users/<int:admin_id>/impersonate/", views.superadmin_impersonate, name="superadmin_user_impersonate"),
]
