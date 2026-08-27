import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import BusinessProfile, AppSettings, Client, Invoice

User = get_user_model()

@pytest.fixture(autouse=True)
def test_email_backend(settings):
    """
    Ensure all tests use in-memory email backend so no real emails are ever sent.
    """
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "test-noreply@invoiceflow.com"


@pytest.fixture
def api_client():
    """
    Returns an unauthenticated DRF APIClient.
    """
    return APIClient()


@pytest.fixture
def test_password():
    return "SmokeTestSecurePass123!"


@pytest.fixture
def admin_user(db, test_password):
    """
    Creates an active Admin / Staff user with BusinessProfile and AppSettings.
    """
    user = User.objects.create_user(
        username="smoke_admin_user",
        email="smoke_admin@example.com",
        password=test_password,
        first_name="Smoke Admin",
        is_staff=True,
        is_superuser=True,
    )
    business = BusinessProfile.objects.create(
        owner=user,
        business_name="Smoke Admin Enterprise",
        email=user.email,
    )
    AppSettings.objects.create(
        business=business,
    )
    return user


@pytest.fixture
def client_user(db, test_password):
    """
    Creates a standard Client user (non-staff).
    """
    user = User.objects.create_user(
        username="smoke_client_user",
        email="smoke_client@example.com",
        password=test_password,
        first_name="Smoke Client",
        is_staff=False,
    )
    business = BusinessProfile.objects.create(
        owner=user,
        business_name="Smoke Client Corp",
        email=user.email,
    )
    AppSettings.objects.create(
        business=business,
    )
    return user


@pytest.fixture
def admin_auth_client(admin_user):
    """
    Returns an APIClient authenticated with admin_user JWT Bearer token.
    """
    client = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


@pytest.fixture
def client_auth_client(client_user):
    """
    Returns an APIClient authenticated with client_user JWT Bearer token.
    """
    client = APIClient()
    refresh = RefreshToken.for_user(client_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


@pytest.fixture
def mock_google_tokeninfo():
    """
    Mocks requests.get to Google tokeninfo endpoint so tests never call external Google servers
    or expose real secrets.
    """
    with patch("api.auth.views.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "email": "google_test_user@gmail.com",
            "email_verified": "true",
            "name": "Google Smoke User",
            "given_name": "Google",
            "family_name": "Smoke",
            "picture": "https://lh3.googleusercontent.com/a/test",
            "sub": "123456789012345678901",
            "aud": getattr(settings, "GOOGLE_CLIENT_ID", ""),
        }
        mock_get.return_value = mock_response
        yield mock_get
