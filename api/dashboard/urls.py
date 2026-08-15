from django.urls import path
from .views import dashboard, dashboard_summary, recent_invoices, recent_payments, search

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("summary/", dashboard_summary, name="dashboard-summary"),
    path("recent-invoices/", recent_invoices, name="dashboard-recent-invoices"),
    path("recent-payments/", recent_payments, name="dashboard-recent-payments"),
    path("search/", search, name="dashboard-search"),
]
