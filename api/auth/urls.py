from django.urls import path

from .views import (
    register,
    request_signup_otp,
    verify_signup_otp,
    resend_signup_otp,
    login,
    google_auth,
    me,
    refresh,
    logout,
    change_password,
    forgot_password,
    resend_password_reset_otp,
    reset_password,
)


urlpatterns = [
    path(
        "",
        me,
        name="auth-index",
    ),

    path(
        "register/",
        register,
        name="auth-register",
    ),

    path(
        "register/request-otp/",
        request_signup_otp,
        name="auth-request-signup-otp",
    ),

    path(
        "register/verify-otp/",
        verify_signup_otp,
        name="auth-verify-signup-otp",
    ),

    path(
        "register/resend-otp/",
        resend_signup_otp,
        name="auth-resend-signup-otp",
    ),


    path(
        "login/",
        login,
        name="auth-login",
    ),

    path(
        "google/",
        google_auth,
        name="auth-google",
    ),

    path(
        "me/",
        me,
        name="auth-me",
    ),

    path(
        "refresh/",
        refresh,
        name="auth-refresh",
    ),

    path(
        "logout/",
        logout,
        name="auth-logout",
    ),

    path(
        "change-password/",
        change_password,
        name="auth-change-password",
    ),

    path(
        "forgot-password/",
        forgot_password,
        name="auth-forgot-password",
    ),

    path(
        "forgot-password/resend-otp/",
        resend_password_reset_otp,
        name="auth-forgot-password-resend-otp",
    ),

    path(
        "reset-password/",
        reset_password,
        name="auth-reset-password",
    ),
]