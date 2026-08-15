from django.urls import path
from .views import receipt_list, receipt_detail, receipt_pdf

urlpatterns = [
    path("", receipt_list, name="receipt-list"),
    path("<int:pk>/pdf/", receipt_pdf, name="receipt-pdf"),
    path("<int:pk>/", receipt_detail, name="receipt-detail"),
]
