from django.urls import path
from .views import profile_detail, profile_update, profile_logo

urlpatterns = [
    path("", profile_detail, name="profile-detail"),
    path("update/", profile_update, name="profile-update"),
    path("logo/", profile_logo, name="profile-logo"),
]
