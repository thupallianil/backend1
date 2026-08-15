from django.urls import path

from .views import (
    register,
    login,
    me,
    refresh,
    logout,
    change_password,
    forgot_password,
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
        "login/",
        login,
        name="auth-login",
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
        "reset-password/",
        reset_password,
        name="auth-reset-password",
    ),
]