from django.urls import path
from .views import (
    payment_list_create, payment_detail,
    create_payment_order, verify_payment,
    payment_webhook, manual_payment,
)

urlpatterns = [
    path("", payment_list_create, name="payment-list-create"),
    path("create-order/", create_payment_order, name="payment-create-order"),
    path("verify/", verify_payment, name="payment-verify"),
    path("webhook/", payment_webhook, name="payment-webhook"),
    path("manual/", manual_payment, name="payment-manual"),
    path("<int:pk>/", payment_detail, name="payment-detail"),
]
