from django.urls import path
from .views import (
    invoice_list_create, invoice_from_quote,
    invoice_detail, invoice_pdf, send_invoice,
)

urlpatterns = [
    path("", invoice_list_create, name="invoice-list-create"),
    path("from-quote/", invoice_from_quote, name="invoice-from-quote"),
    path("<int:pk>/pdf/", invoice_pdf, name="invoice-pdf"),
    path("<int:pk>/send/", send_invoice, name="invoice-send"),
    path("<int:pk>/", invoice_detail, name="invoice-detail"),
]
