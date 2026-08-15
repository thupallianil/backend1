from django.urls import path
from .views import (
    quote_list_create, quote_detail,
    approve_quote, reject_quote, convert_to_invoice,
    sync_invoice_from_quote,
    quote_pdf,
)

urlpatterns = [
    path("", quote_list_create, name="quote-list-create"),
    path("<int:pk>/approve/", approve_quote, name="quote-approve"),
    path("<int:pk>/reject/", reject_quote, name="quote-reject"),
    path("<int:pk>/convert-to-invoice/", convert_to_invoice, name="quote-convert-to-invoice"),
    path("<int:pk>/sync-invoice/", sync_invoice_from_quote, name="quote-sync-invoice"),
    path("<int:pk>/pdf/", quote_pdf, name="quote-pdf"),
    path("<int:pk>/", quote_detail, name="quote-detail"),
]
