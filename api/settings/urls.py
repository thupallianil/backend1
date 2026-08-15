from django.urls import path
from .views import settings_detail

urlpatterns = [
    path("", settings_detail, name="settings-detail"),
]
