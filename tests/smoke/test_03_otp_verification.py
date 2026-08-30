import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from api.models import SignupVerificationOTP, BusinessProfile, AppSettings

User = get_user_model()

@pytest.mark.smoke
@pytest.mark.django_db
def test_otp_verification_success_creates_account(api_client):
    """
    3. Email OTP verification: Submitting correct OTP creates User + BusinessProfile + AppSettings,
       and returns authentication tokens.
    """
    email = "verified.user@startup.io"
    
    # Step 1: Request OTP
    req_payload = {
        "name": "Sarah Connor",
        "email": email,
        "company_name": "Cyberdyne Systems",
        "password": "StrongPassword999!",
        "password_confirm": "StrongPassword999!",
        "role": "ADMIN",
    }
    req_res = api_client.post("/api/auth/register/request-otp/", req_payload, format="json")
    assert req_res.status_code == 200

    otp_record = SignupVerificationOTP.objects.get(email=email)
    correct_otp = otp_record.otp_code

    # Step 2: Verify with correct OTP
    verify_payload = {
        "email": email,
        "otp": correct_otp,
    }
    verify_res = api_client.post("/api/auth/register/verify-otp/", verify_payload, format="json")
    assert verify_res.status_code == 201, f"Expected 201 Created, got {verify_res.status_code}: {verify_res.content}"

    body = verify_res.json()
    assert body.get("success") is True
    assert "access" in body.get("data", {}) or "token" in body.get("data", {})
    assert "user" in body.get("data", {})

    # Confirm user exists in DB
    created_user = User.objects.filter(email__iexact=email).first()
    assert created_user is not None, "User was not created in database after OTP verification"
    assert created_user.first_name == "Sarah Connor"
    assert created_user.is_staff is True

    # Confirm BusinessProfile and AppSettings exist
    business = BusinessProfile.objects.filter(owner=created_user).first()
    assert business is not None, "BusinessProfile was not created for verified user"
    assert business.business_name == "Cyberdyne Systems"
    assert AppSettings.objects.filter(business=business).exists(), "AppSettings was not created"


@pytest.mark.smoke
@pytest.mark.django_db
def test_otp_verification_rejects_incorrect_otp(api_client):
    """
    3. Email OTP verification: Submitting wrong OTP returns 400 and does NOT create user.
    """
    email = "wrong.otp.test@startup.io"
    
    req_payload = {
        "name": "Wrong OTP Tester",
        "email": email,
        "password": "StrongPassword999!",
        "password_confirm": "StrongPassword999!",
    }
    api_client.post("/api/auth/register/request-otp/", req_payload, format="json")

    # Verify with WRONG OTP
    verify_res = api_client.post(
        "/api/auth/register/verify-otp/",
        {"email": email, "otp": "000000"},
        format="json",
    )
    assert verify_res.status_code == 400
    assert verify_res.json().get("success") is False
    assert not User.objects.filter(email__iexact=email).exists()


@pytest.mark.smoke
@pytest.mark.django_db
def test_otp_verification_rejects_expired_otp(api_client):
    """
    3. Email OTP verification: Submitting expired OTP returns 400.
    """
    email = "expired.otp.test@startup.io"
    
    req_payload = {
        "name": "Expired Tester",
        "email": email,
        "password": "StrongPassword999!",
        "password_confirm": "StrongPassword999!",
    }
    api_client.post("/api/auth/register/request-otp/", req_payload, format="json")

    # Manually expire the OTP record
    otp_record = SignupVerificationOTP.objects.get(email=email)
    otp_record.expires_at = timezone.now() - timedelta(minutes=5)
    otp_record.save()

    verify_res = api_client.post(
        "/api/auth/register/verify-otp/",
        {"email": email, "otp": otp_record.otp_code},
        format="json",
    )
    assert verify_res.status_code == 400
    assert "expired" in verify_res.json().get("message", "").lower()
    assert not User.objects.filter(email__iexact=email).exists()


@pytest.mark.smoke
@pytest.mark.django_db
def test_resend_otp_generates_new_code(api_client):
    """
    3. Email OTP verification: Resend OTP generates and sends a new valid OTP.
    """
    email = "resend.test@startup.io"
    
    req_payload = {
        "name": "Resend Tester",
        "email": email,
        "password": "StrongPassword999!",
        "password_confirm": "StrongPassword999!",
    }
    api_client.post("/api/auth/register/request-otp/", req_payload, format="json")
    record = SignupVerificationOTP.objects.get(email=email)
    record.created_at = timezone.now() - timezone.timedelta(seconds=65)
    record.save(update_fields=["created_at"])

    # Trigger resend OTP
    resend_res = api_client.post("/api/auth/register/resend-otp/", {"email": email}, format="json")
    assert resend_res.status_code == 200
    assert resend_res.json().get("success") is True

    # New OTP is saved in database and can verify successfully
    new_otp_record = SignupVerificationOTP.objects.get(email=email)
    new_otp = new_otp_record.otp_code

    verify_res = api_client.post(
        "/api/auth/register/verify-otp/",
        {"email": email, "otp": new_otp},
        format="json",
    )
    assert verify_res.status_code == 201
    assert User.objects.filter(email__iexact=email).exists()
