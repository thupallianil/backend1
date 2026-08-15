from django.urls import path
from .views import dashboard, sales, payments, tax, clients, profit_loss

urlpatterns = [
    path("", dashboard, name="reports-dashboard"),
    path("dashboard/", dashboard, name="reports-dashboard-detail"),
    path("sales/", sales, name="reports-sales"),
    path("payments/", payments, name="reports-payments"),
    path("tax/", tax, name="reports-tax"),
    path("clients/", clients, name="reports-clients"),
    path("profit-loss/", profit_loss, name="reports-profit-loss"),
]
