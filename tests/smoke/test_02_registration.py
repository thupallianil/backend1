import pytest
from django.core import mail
from django.contrib.auth import get_user_model
from api.models import SignupVerificationOTP

User = get_user_model()

@pytest.mark.smoke
@pytest.mark.django_db
def test_registration_request_otp_success_and_no_premature_user(api_client):
    """
    2. User registration: Valid input triggers OTP generation and email dispatch,
       WITHOUT creating a permanent user record in the database prior to verification.
    """
    payload = {
        "name": "Alex Mercer",
        "email": "alex.mercer@company.org",
        "company_name": "Mercer Innovations",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
        "role": "ADMIN",
    }

    # Verify user does not exist prior to registration request
    assert not User.objects.filter(email__iexact=payload["email"]).exists()

    response = api_client.post("/api/auth/register/request-otp/", payload, format="json")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.content}"

    body = response.json()
    assert body.get("success") is True
    assert "email" in body.get("data", {})
    assert body["data"]["email"] == payload["email"]

    # CRITICAL CHECK: User record MUST NOT exist in database yet
    assert not User.objects.filter(email__iexact=payload["email"]).exists(), (
        "CRITICAL ERROR: Permanent User account was created in DB before OTP verification!"
    )

    # Verify SignupVerificationOTP model record was created
    otp_record = SignupVerificationOTP.objects.filter(email=payload["email"]).first()
    assert otp_record is not None, "SignupVerificationOTP record was not saved to database"
    assert len(otp_record.otp_code) == 6, f"Expected 6-digit OTP, got {otp_record.otp_code}"

    # Verify email was dispatched via in-memory backend
    assert len(mail.outbox) >= 1, "No email was dispatched to mail.outbox"
    sent_email = mail.outbox[-1]
    assert payload["email"] in sent_email.to
    assert otp_record.otp_code in sent_email.body or otp_record.otp_code in (sent_email.alternatives[0][0] if sent_email.alternatives else "")


@pytest.mark.smoke
@pytest.mark.django_db
def test_registration_validation_errors(api_client):
    """
    2. User registration: Verify validation error responses for invalid inputs.
    """
    # 1. Missing required fields
    res_empty = api_client.post("/api/auth/register/request-otp/", {}, format="json")
    assert res_empty.status_code == 400
    assert res_empty.json().get("success") is False

    # 2. Passwords mismatch
    mismatch_payload = {
        "name": "Jane Doe",
        "email": "jane.doe@company.org",
        "password": "Password123!",
        "password_confirm": "DifferentPassword456!",
    }
    res_mismatch = api_client.post("/api/auth/register/request-otp/", mismatch_payload, format="json")
    assert res_mismatch.status_code == 400
    res_str = str(res_mismatch.json()).lower()
    assert "match" in res_str or "password_confirm" in res_mismatch.json().get("errors", {})

    # 3. Disposable/fake email domain
    disposable_payload = {
        "name": "Scam User",
        "email": "scam@mailinator.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }
    res_disp = api_client.post("/api/auth/register/request-otp/", disposable_payload, format="json")
    assert res_disp.status_code == 400
    assert "disposable" in str(res_disp.json()).lower() or "email" in res_disp.json().get("errors", {})

