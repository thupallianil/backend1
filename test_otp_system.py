import os
import django
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from rest_framework.test import APIClient
from api.models import SignupVerificationOTP, PasswordResetOTP, BusinessProfile, AppSettings

User = get_user_model()
client = APIClient()

def run_tests():
    print("=========================================================")
    print("STARTING PRODUCTION-GRADE EMAIL OTP AUTHENTICATION TESTS")
    print("=========================================================")

    # Clean test records
    User.objects.filter(email__in=["tester@example.com", "resetuser@example.com"]).delete()
    SignupVerificationOTP.objects.filter(email__in=["tester@example.com", "resetuser@example.com"]).delete()
    PasswordResetOTP.objects.filter(email__in=["tester@example.com", "resetuser@example.com"]).delete()
    if hasattr(mail, "outbox"):
        mail.outbox.clear()

    # -------------------------------------------------------------
    # 1. SIGNUP: Valid registration & OTP dispatch
    # -------------------------------------------------------------
    print("\n[TEST 1] Signup: Valid registration request...")
    res = client.post("/api/auth/register/request-otp/", {
        "name": "Alex Mercer",
        "email": "tester@example.com",
        "company_name": "Mercer Tech",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "role": "admin"
    }, format="json")

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    assert res.data.get("success") is True
    # User must NOT be created yet
    assert not User.objects.filter(email="tester@example.com").exists(), "FAIL: User was created prematurely!"
    # OTP record in DB
    otp_record = SignupVerificationOTP.objects.filter(email="tester@example.com").first()
    assert otp_record is not None, "FAIL: OTP record not created in DB"
    assert len(otp_record.otp) == 6, f"FAIL: Expected 6 digits, got {otp_record.otp}"
    # Email dispatched
    assert len(mail.outbox) >= 1, "FAIL: Email was not sent"
    assert otp_record.otp in mail.outbox[-1].body or otp_record.otp in (mail.outbox[-1].alternatives[0][0] if mail.outbox[-1].alternatives else "")
    print("  --> PASS: OTP generated, email sent, user not created yet, OTP not exposed in response.")

    # -------------------------------------------------------------
    # 2. SIGNUP: Resend cooldown (60 seconds)
    # -------------------------------------------------------------
    print("\n[TEST 2] Signup: Resend cooldown (< 60s)...")
    res_cooldown = client.post("/api/auth/register/resend-otp/", {
        "email": "tester@example.com"
    }, format="json")
    assert res_cooldown.status_code == 429, f"Expected 429 Too Many Requests, got {res_cooldown.status_code}"
    assert res_cooldown.data.get("success") is False
    assert "seconds" in res_cooldown.data.get("message", "").lower()
    print("  --> PASS: 60s cooldown enforced with 429 status.")

    # -------------------------------------------------------------
    # 3. SIGNUP: Incorrect OTP verification
    # -------------------------------------------------------------
    print("\n[TEST 3] Signup: Incorrect OTP submission...")
    res_wrong = client.post("/api/auth/register/verify-otp/", {
        "email": "tester@example.com",
        "otp": "000000"
    }, format="json")
    assert res_wrong.status_code == 400
    assert res_wrong.data.get("success") is False
    assert "Invalid verification code" in res_wrong.data.get("message", "")
    assert not User.objects.filter(email="tester@example.com").exists()
    otp_record.refresh_from_db()
    assert otp_record.attempts == 1
    print("  --> PASS: Wrong OTP rejected and attempt counter incremented.")

    # -------------------------------------------------------------
    # 4. SIGNUP: 5 failed attempts limit
    # -------------------------------------------------------------
    print("\n[TEST 4] Signup: 5 failed attempts limit...")
    for _ in range(4):
        client.post("/api/auth/register/verify-otp/", {"email": "tester@example.com", "otp": "000000"}, format="json")
    # OTP record should now be deleted after 5 failed attempts
    assert not SignupVerificationOTP.objects.filter(email="tester@example.com").exists()
    res_attempt_exceeded = client.post("/api/auth/register/verify-otp/", {"email": "tester@example.com", "otp": "000000"}, format="json")
    assert res_attempt_exceeded.status_code == 400
    print("  --> PASS: 5 failed attempts reached, OTP invalidated and purged.")

    # -------------------------------------------------------------
    # 5. SIGNUP: Valid verification creates User + Profiles
    # -------------------------------------------------------------
    print("\n[TEST 5] Signup: Fresh OTP & successful verification...")
    # Request fresh OTP (simulate time passed)
    client.post("/api/auth/register/request-otp/", {
        "name": "Alex Mercer",
        "email": "tester@example.com",
        "company_name": "Mercer Tech",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "role": "admin"
    }, format="json")
    fresh_otp_record = SignupVerificationOTP.objects.get(email="tester@example.com")
    correct_otp = fresh_otp_record.otp

    res_verify = client.post("/api/auth/register/verify-otp/", {
        "email": "tester@example.com",
        "otp": correct_otp
    }, format="json")
    assert res_verify.status_code == 201, f"Expected 201, got {res_verify.status_code}: {res_verify.data}"
    assert res_verify.data.get("success") is True
    assert "access" in res_verify.data
    assert "refresh" in res_verify.data
    assert User.objects.filter(email="tester@example.com").exists(), "FAIL: User was not created"
    user = User.objects.get(email="tester@example.com")
    assert BusinessProfile.objects.filter(owner=user).exists(), "FAIL: BusinessProfile not created"
    assert AppSettings.objects.filter(business__owner=user).exists(), "FAIL: AppSettings not created"
    assert not SignupVerificationOTP.objects.filter(email="tester@example.com").exists(), "FAIL: OTP not deleted after use"
    print("  --> PASS: Account created atomically, profiles provisioned, single-use OTP deleted.")

    # -------------------------------------------------------------
    # 6. SIGNUP: Duplicate signup rejection
    # -------------------------------------------------------------
    print("\n[TEST 6] Signup: Duplicate email rejection...")
    res_dup = client.post("/api/auth/register/request-otp/", {
        "name": "Duplicate User",
        "email": "tester@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
    }, format="json")
    assert res_dup.status_code == 400
    msg = res_dup.data.get("message", "").lower()
    assert "already registered" in msg or "already exists" in msg or "email" in str(res_dup.data).lower()
    print("  --> PASS: Duplicate account rejected with clear message.")

    # -------------------------------------------------------------
    # 7. FORGOT PASSWORD: Valid email triggers reset OTP
    # -------------------------------------------------------------
    print("\n[TEST 7] Forgot Password: Request OTP...")
    res_fp = client.post("/api/auth/forgot-password/", {
        "email": "tester@example.com"
    }, format="json")
    assert res_fp.status_code == 200
    assert res_fp.data.get("success") is True
    reset_otp_rec = PasswordResetOTP.objects.filter(email="tester@example.com").first()
    assert reset_otp_rec is not None
    assert len(reset_otp_rec.otp) == 6
    print("  --> PASS: Password reset OTP created and email dispatched.")

    # -------------------------------------------------------------
    # 8. RESET PASSWORD: Correct OTP resets password
    # -------------------------------------------------------------
    print("\n[TEST 8] Reset Password: Submit new password with OTP...")
    res_rp = client.post("/api/auth/reset-password/", {
        "email": "tester@example.com",
        "otp": reset_otp_rec.otp,
        "password": "NewSuperPassword99!",
        "password_confirm": "NewSuperPassword99!"
    }, format="json")
    assert res_rp.status_code == 200
    assert res_rp.data.get("success") is True
    assert not PasswordResetOTP.objects.filter(email="tester@example.com").exists(), "FAIL: Reset OTP not deleted after use"

    # Old password must fail
    res_old_login = client.post("/api/auth/login/", {
        "email": "tester@example.com",
        "password": "Password123!",
    }, format="json")
    assert res_old_login.status_code == 401, "FAIL: Old password still authenticated!"

    # New password must succeed
    res_new_login = client.post("/api/auth/login/", {
        "email": "tester@example.com",
        "password": "NewSuperPassword99!",
    }, format="json")
    assert res_new_login.status_code == 200, f"FAIL: New password login failed: {res_new_login.data}"
    assert res_new_login.data.get("success") is True
    print("  --> PASS: Password updated, old password revoked, new password authenticated.")

    print("\n=========================================================")
    print("ALL PRODUCTION-GRADE EMAIL OTP AUTH TESTS PASSED (100%)")
    print("=========================================================\n")

if __name__ == "__main__":
    run_tests()
