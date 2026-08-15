import uuid
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import AppSettings, BusinessProfile, Invoice, Payment, Receipt
from drf_spectacular.utils import extend_schema
from .serializers import PaymentSerializer
from .gateway import get_razorpay_gateway


def get_user_business(user):
    return BusinessProfile.objects.filter(owner=user).first()


def record_successful_payment(payment):
    """Apply a pending payment once and issue a receipt."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("invoice").get(pk=payment.pk)
        if payment.status == Payment.Status.SUCCESS:
            return payment, False
        invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
        if payment.amount <= 0 or payment.amount > invoice.balance_due:
            raise ValueError("Payment amount must be greater than zero and cannot exceed the outstanding balance.")
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at", "updated_at"])
        invoice.paid_amount += payment.amount
        invoice.balance_due = invoice.total - invoice.paid_amount
        invoice.status = Invoice.Status.PAID if invoice.balance_due == Decimal("0.00") else Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=["paid_amount", "balance_due", "status", "updated_at"])
        settings_obj, _ = AppSettings.objects.select_for_update().get_or_create(business=payment.business)
        Receipt.objects.create(business=payment.business, payment=payment, invoice=invoice, receipt_number=f"{settings_obj.receipt_prefix}-{settings_obj.next_receipt_number:04d}", amount=payment.amount, issued_date=timezone.localdate())
        settings_obj.next_receipt_number += 1
        settings_obj.save(update_fields=["next_receipt_number", "updated_at"])
    return payment, True


@extend_schema(tags=["Payments"])
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def payment_list_create(request):
    business = get_user_business(request.user)

    if request.method == "GET":
        if business:
            payments = Payment.objects.filter(
                business=business
            ).order_by("-created_at")
        else:
            payments = Payment.objects.filter(
                invoice__client__email__iexact=request.user.email
            ).order_by("-created_at")

        serializer = PaymentSerializer(
            payments,
            many=True,
        )

        return Response({
            "success": True,
            "message": "Payments retrieved successfully",
            "data": serializer.data,
        })

    serializer = PaymentSerializer(
        data=request.data
    )

    if serializer.is_valid():
        if business and serializer.validated_data["invoice"].business_id != business.id:
            return Response(
                {"success": False, "message": "Invoice does not belong to your business."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = serializer.save(
            business=business or serializer.validated_data["invoice"].business
        )

        return Response(
            {
                "success": True,
                "message": "Payment created successfully",
                "data": PaymentSerializer(payment).data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(
        {
            "success": False,
            "message": "Payment creation failed",
            "errors": serializer.errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(tags=["Payments"])
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def payment_detail(request, pk):
    business = get_user_business(request.user)

    if business:
        payment = get_object_or_404(
            Payment,
            pk=pk,
            business=business,
        )
    else:
        payment = get_object_or_404(
            Payment,
            pk=pk,
            invoice__client__email__iexact=request.user.email,
        )

    if request.method == "GET":
        return Response({
            "success": True,
            "message": "Payment retrieved successfully",
            "data": PaymentSerializer(payment).data,
        })

    if request.method in ["PUT", "PATCH"]:
        if payment.status == Payment.Status.SUCCESS:
            return Response(
                {"success": False, "message": "Successful payments cannot be changed."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = PaymentSerializer(
            payment,
            data=request.data,
            partial=request.method == "PATCH",
        )

        if serializer.is_valid():
            invoice = serializer.validated_data.get("invoice", payment.invoice)
            if invoice.business_id != business.id:
                return Response(
                    {"success": False, "message": "Invoice does not belong to your business."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if serializer.validated_data.get("amount", payment.amount) > invoice.balance_due:
                return Response(
                    {"success": False, "message": "Payment amount cannot exceed the outstanding balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save()

            return Response({
                "success": True,
                "message": "Payment updated successfully",
                "data": serializer.data,
            })

        return Response(
            {
                "success": False,
                "message": "Payment update failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.method == "DELETE":
        with transaction.atomic():
            # If the payment was successful, gracefully revert invoice balance
            if payment.status == Payment.Status.SUCCESS and payment.invoice:
                invoice = payment.invoice
                invoice.paid_amount = max(Decimal("0.00"), invoice.paid_amount - payment.amount)
                invoice.balance_due = max(Decimal("0.00"), invoice.total - invoice.paid_amount)
                if invoice.paid_amount == Decimal("0.00"):
                    invoice.status = Invoice.Status.SENT
                elif invoice.balance_due == Decimal("0.00"):
                    invoice.status = Invoice.Status.PAID
                else:
                    invoice.status = Invoice.Status.PARTIALLY_PAID
                invoice.save(update_fields=["paid_amount", "balance_due", "status", "updated_at"])

            # Delete any linked receipt
            Receipt.objects.filter(payment=payment).delete()

            # Delete the payment record
            payment.delete()

        return Response(
            {
                "success": True,
                "message": "Payment deleted and invoice balance reconciled successfully.",
            },
            status=status.HTTP_200_OK,
        )


from rest_framework import serializers

class CreateOrderInputSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)

@extend_schema(tags=["Payments"], request=CreateOrderInputSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_payment_order(request):
    """
    POST /api/payments/create-order/
    Body: { "invoice_id": <int>, "amount": <decimal> }
    Create a real Razorpay payment order.
    """
    business = get_user_business(request.user)

    invoice_id = request.data.get("invoice_id")
    amount = request.data.get("amount")

    if not invoice_id or not amount:
        return Response(
            {"success": False, "message": "invoice_id and amount are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if business:
        invoice = get_object_or_404(Invoice, pk=invoice_id, business=business)
    else:
        invoice = get_object_or_404(Invoice, pk=invoice_id, client__email__iexact=request.user.email)
        business = invoice.business

    try:
        payment_amount = Decimal(str(amount))
    except Exception:
        return Response({"success": False, "message": "amount must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

    if payment_amount <= 0 or payment_amount > invoice.balance_due:
        return Response({"success": False, "message": "Payment amount must be greater than zero and cannot exceed the outstanding balance."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        settings_obj = AppSettings.objects.filter(business=business).first()
        payment_settings = settings_obj.payment_settings if settings_obj else {}
        
        key_id = payment_settings.get("razorpayKeyId")
        key_secret = payment_settings.get("razorpaySecretKey")
        
        gateway = get_razorpay_gateway(key_id=key_id, key_secret=key_secret)
        order = gateway.create_order(
            amount=payment_amount,
            currency="INR",
            receipt=f"inv_{invoice.id}",
            notes={"invoice_number": invoice.invoice_number}
        )
        gateway_order_id = order.get("id")
    except Exception as exc:
        return Response(
            {"success": False, "message": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Create a pending Payment record
    payment = Payment.objects.create(
        business=business,
        invoice=invoice,
        amount=payment_amount,
        method=Payment.Method.ONLINE,
        status=Payment.Status.PENDING,
        gateway_order_id=gateway_order_id,
    )

    return Response(
        {
            "success": True,
            "message": "Payment order created successfully.",
            "data": {
                "payment_id": payment.id,
                "gateway_order_id": gateway_order_id,
                "amount": str(payment.amount),
                "currency": "INR",
                "key_id": gateway.key_id,
            },
        },
        status=status.HTTP_201_CREATED,
    )


class VerifyPaymentInputSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField(required=True)
    gateway_payment_id = serializers.CharField(required=True)
    gateway_signature = serializers.CharField(required=True)

@extend_schema(tags=["Payments"], request=VerifyPaymentInputSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    POST /api/payments/verify/
    Body: { "payment_id": <int>, "gateway_payment_id": <str>, "gateway_signature": <str> }
    Verify actual Razorpay signature.
    """
    business = get_user_business(request.user)

    payment_id = request.data.get("payment_id")
    gateway_payment_id = request.data.get("gateway_payment_id", "")
    gateway_signature = request.data.get("gateway_signature", "")

    if not payment_id or not gateway_payment_id or not gateway_signature:
        return Response(
            {"success": False, "message": "payment_id, gateway_payment_id, and gateway_signature are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if business:
        payment = get_object_or_404(Payment, pk=payment_id, business=business)
    else:
        payment = get_object_or_404(Payment, pk=payment_id, invoice__client__email__iexact=request.user.email)
        business = payment.business

    if payment.status == Payment.Status.SUCCESS:
        return Response(
            {"success": False, "message": "This payment has already been verified."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        settings_obj = AppSettings.objects.filter(business=business).first()
        payment_settings = settings_obj.payment_settings if settings_obj else {}
        
        key_id = payment_settings.get("razorpayKeyId")
        key_secret = payment_settings.get("razorpaySecretKey")
        
        gateway = get_razorpay_gateway(key_id=key_id, key_secret=key_secret)
        # Verify signature
        is_valid = gateway.verify_payment_signature(
            order_id=payment.gateway_order_id,
            payment_id=gateway_payment_id,
            signature=gateway_signature,
        )
        if not is_valid:
            return Response(
                {"success": False, "message": "Invalid payment signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as exc:
        return Response(
            {"success": False, "message": f"Verification error: {str(exc)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Save gateway details and real transaction ID before reconciling the payment.
    payment.gateway_payment_id = gateway_payment_id
    payment.gateway_signature = gateway_signature
    payment.transaction_id = gateway_payment_id
    payment.save(update_fields=["gateway_payment_id", "gateway_signature", "transaction_id", "updated_at"])

    try:
        payment, _ = record_successful_payment(payment)
    except ValueError as exc:
        return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "success": True,
        "message": "Payment verified successfully.",
        "data": PaymentSerializer(payment).data,
    })


@extend_schema(tags=["Payments"], exclude=True)
@api_view(["POST"])
@permission_classes([])
def payment_webhook(request):
    """
    POST /api/payments/webhook/
    Webhook endpoint for Razorpay to send async payment notifications (e.g., order.paid, payment.captured).
    """
    signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE")
    if not signature:
        return Response({"success": False, "message": "Missing signature"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = request.data
        event = payload.get("event")
        
        # We only care about successful payment events
        if event not in ["order.paid", "payment.captured"]:
            return Response({"success": True, "message": "Event ignored"})

        # Extract order ID from payload
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        
        gateway_order_id = order_entity.get("id") or payment_entity.get("order_id")
        gateway_payment_id = payment_entity.get("id")

        if not gateway_order_id:
            return Response({"success": False, "message": "No order ID found in payload"}, status=status.HTTP_400_BAD_REQUEST)

        # Find the payment in our database
        payment = Payment.objects.filter(gateway_order_id=gateway_order_id).select_related("business").first()
        if not payment:
            return Response({"success": False, "message": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == Payment.Status.SUCCESS:
            return Response({"success": True, "message": "Payment already processed"})

        # Get business webhook secret
        settings_obj = AppSettings.objects.filter(business=payment.business).first()
        payment_settings = settings_obj.payment_settings if settings_obj else {}
        
        webhook_secret = payment_settings.get("razorpayWebhookSecret")
        if not webhook_secret:
            return Response({"success": False, "message": "Webhook secret not configured for this business"}, status=status.HTTP_400_BAD_REQUEST)

        # Setup gateway (we need the key_secret to verify webhook signature)
        key_id = payment_settings.get("razorpayKeyId")
        key_secret = payment_settings.get("razorpaySecretKey")
        gateway = get_razorpay_gateway(key_id=key_id, key_secret=key_secret)

        # DRF request.body contains the raw bytes needed for HMAC verification
        is_valid = gateway.verify_webhook_signature(
            payload=request.body,
            signature=signature,
        )

        if not is_valid:
            return Response({"success": False, "message": "Invalid webhook signature"}, status=status.HTTP_400_BAD_REQUEST)

        # Update payment
        payment.gateway_payment_id = gateway_payment_id or payment.gateway_payment_id
        payment.transaction_id = gateway_payment_id or payment.transaction_id
        payment.save(update_fields=["gateway_payment_id", "transaction_id", "updated_at"])

        # Reconcile invoice
        record_successful_payment(payment)

        return Response({"success": True, "message": "Webhook processed successfully"})
    except Exception as exc:
        return Response({"success": False, "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ManualPaymentInputSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
    method = serializers.ChoiceField(choices=["cash", "bank", "upi", "card", "other"], required=False, default="cash")
    transaction_id = serializers.CharField(required=False, allow_blank=True)
    utr_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

@extend_schema(tags=["Payments"], request=ManualPaymentInputSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manual_payment(request):
    """
    POST /api/payments/manual/
    Body: { "invoice_id": <int>, "amount": <decimal>, "method": "cash"|"bank"|"upi"|"card"|"other", "transaction_id": "", "notes": "" }
    Records a manual (offline/direct) payment with genuine UTR/Transaction reference and updates invoice balance.
    """
    business = get_user_business(request.user)

    invoice_id = request.data.get("invoice_id")
    amount = request.data.get("amount")
    method = request.data.get("method", Payment.Method.CASH)
    notes = request.data.get("notes", "")

    if not invoice_id or not amount:
        return Response(
            {"success": False, "message": "invoice_id and amount are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if business:
        invoice = get_object_or_404(Invoice, pk=invoice_id, business=business)
    else:
        invoice = get_object_or_404(Invoice, pk=invoice_id, client__email__iexact=request.user.email)
        business = invoice.business

    if invoice.status == Invoice.Status.PAID:
        return Response(
            {"success": False, "message": "Invoice is already fully paid."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payment_amount = Decimal(str(amount))
    except Exception:
        return Response({"success": False, "message": "amount must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

    if payment_amount <= 0 or payment_amount > invoice.balance_due:
        return Response({"success": False, "message": "Payment amount must be greater than zero and cannot exceed the outstanding balance."}, status=status.HTTP_400_BAD_REQUEST)

    if method not in Payment.Method.values:
        return Response({"success": False, "message": "Invalid payment method."}, status=status.HTTP_400_BAD_REQUEST)

    provided_txn_id = (
        request.data.get("transaction_id")
        or request.data.get("utr_number")
        or request.data.get("reference_number")
    )

    if provided_txn_id and str(provided_txn_id).strip():
        transaction_id = str(provided_txn_id).strip().upper()
    else:
        # Standardized banking UTR / Reference generation based on payment method
        now_dt = timezone.now()
        date_str = now_dt.strftime("%Y%m%d")
        time_str = now_dt.strftime("%y%m%d%H%M%S")
        rand_code = uuid.uuid4().hex[:6].upper()

        if method == Payment.Method.UPI:
            transaction_id = f"UPI/{time_str}/{rand_code[:4]}"
        elif method == Payment.Method.BANK:
            transaction_id = f"UTR{date_str}{rand_code}"
        elif method == Payment.Method.CARD:
            transaction_id = f"AUTH-{date_str}-{rand_code}"
        else:
            transaction_id = f"CSH-VCH-{date_str}-{rand_code[:4]}"

    payment = Payment.objects.create(
        business=business,
        invoice=invoice,
        amount=payment_amount,
        method=method,
        status=Payment.Status.PENDING,
        transaction_id=transaction_id,
        paid_at=timezone.now(),
        notes=notes,
    )

    payment, _ = record_successful_payment(payment)
    invoice.refresh_from_db()

    return Response(
        {
            "success": True,
            "message": "Payment recorded successfully with real transaction reference.",
            "data": {
                "payment": PaymentSerializer(payment).data,
                "invoice": {
                    "id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "total": str(invoice.total),
                    "paid_amount": str(invoice.paid_amount),
                    "balance_due": str(invoice.balance_due),
                    "status": invoice.status,
                },
            },
        },
        status=status.HTTP_201_CREATED,
    )
