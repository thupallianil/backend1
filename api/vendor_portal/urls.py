from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.vendor_dashboard, name="vendor_dashboard"),
    path("orders/", views.vendor_orders, name="vendor_orders"),
    path("invoices/", views.vendor_invoices, name="vendor_invoices"),
    path("payments/", views.vendor_payments, name="vendor_payments"),
    path("profile/", views.vendor_profile, name="vendor_profile"),
]
