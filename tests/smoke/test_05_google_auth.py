import pytest
from django.contrib.auth import get_user_model
from api.models import BusinessProfile, AppSettings

User = get_user_model()

@pytest.mark.smoke
@pytest.mark.django_db
def test_google_auth_endpoint_reachable_and_requires_token(api_client):
    """
    5. Google OAuth: Endpoint is reachable and rejects requests without credential/token.
    """
    response = api_client.post("/api/auth/google/", {}, format="json")
    assert response.status_code == 400
    assert response.json().get("success") is False
    assert "credential" in response.json().get("errors", {}) or "required" in str(response.json()).lower()



@pytest.mark.smoke
@pytest.mark.django_db
def test_google_auth_flow_with_mocked_tokeninfo(api_client, mock_google_tokeninfo):
    """
    5. Google OAuth: Verify safe automated Google login/auto-provisioning using mocked token verification.
       Zero real Google client secrets are exposed.
    """
    payload = {
        "credential": "mocked_google_jwt_token_for_testing",
        "role": "ADMIN",
        "mode": "signup",
    }

    # Verify user does not exist prior to Google login
    assert not User.objects.filter(email="google_test_user@gmail.com").exists()

    response = api_client.post("/api/auth/google/", payload, format="json")
    assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}: {response.content}"

    body = response.json()
    assert body.get("success") is True
    assert "access" in body.get("data", {})
    assert "user" in body.get("data", {})
    assert body["data"]["user"]["email"] == "google_test_user@gmail.com"

    # Confirm user was created in database
    user = User.objects.get(email="google_test_user@gmail.com")
    assert user.first_name in ["Google", "Google Smoke User"]


    # Confirm BusinessProfile and AppSettings exist
    business = BusinessProfile.objects.filter(owner=user).first()
    assert business is not None, "BusinessProfile was not created for Google OAuth user"
    assert AppSettings.objects.filter(business=business).exists()
