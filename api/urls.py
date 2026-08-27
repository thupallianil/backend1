from django.urls import include, path
from .views import api_index, health_check, public_platform_stats

urlpatterns = [
    path("", api_index, name="api-index"),
    path("health/", health_check, name="api-health"),
    path("public-stats/", public_platform_stats, name="public-platform-stats"),
    path("auth/", include("api.auth.urls")),
    path("settings/", include("api.settings.urls")),
    path("profile/", include("api.profile.urls")),
    path("clients/", include("api.clients.urls")),
    path("vendors/", include("api.vendors.urls")),
    path("quotes/", include("api.quotes.urls")),
    path("invoices/", include("api.invoices.urls")),
    path("payments/", include("api.payments.urls")),
    path("receipts/", include("api.receipts.urls")),
    path("dashboard/", include("api.dashboard.urls")),
    path("reports/", include("api.reports.urls")),
    path("tickets/", include("api.tickets.urls")),
    path("notifications/", include("api.notifications.urls")),
]
