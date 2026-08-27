import pytest

@pytest.mark.smoke
@pytest.mark.django_db
def test_login_success_with_valid_credentials(api_client, admin_user, test_password):
    """
    4. Login: Valid credentials return 200 OK with valid JWT access & refresh tokens.
    """
    login_payload = {
        "email": admin_user.email,
        "password": test_password,
        "role": "ADMIN",
    }
    response = api_client.post("/api/auth/login/", login_payload, format="json")
    assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.content}"

    body = response.json()
    assert body.get("success") is True
    data = body.get("data", {})
    assert "access" in data, "Access token missing from login response"
    assert "refresh" in data, "Refresh token missing from login response"
    assert "user" in data, "User object missing from login response"
    assert data["user"]["email"] == admin_user.email


@pytest.mark.smoke
@pytest.mark.django_db
def test_login_rejected_with_invalid_password(api_client, admin_user):
    """
    4. Login: Invalid password must be rejected.
    """
    login_payload = {
        "email": admin_user.email,
        "password": "WrongPassword999!",
    }
    response = api_client.post("/api/auth/login/", login_payload, format="json")
    assert response.status_code in [400, 401], f"Expected 400/401, got {response.status_code}"
    assert response.json().get("success") is False


@pytest.mark.smoke
@pytest.mark.django_db
def test_login_rejected_with_nonexistent_user(api_client):
    """
    4. Login: Non-existent email must be rejected.
    """
    login_payload = {
        "email": "does_not_exist@randomdomain123.com",
        "password": "AnyPassword123!",
    }
    response = api_client.post("/api/auth/login/", login_payload, format="json")
    assert response.status_code in [400, 401]
    assert response.json().get("success") is False


@pytest.mark.smoke
@pytest.mark.django_db
def test_jwt_token_refresh(api_client, admin_user, test_password):
    """
    4. Login: Verify refresh token can be used to obtain a new access token.
    """
    login_res = api_client.post(
        "/api/auth/login/",
        {"email": admin_user.email, "password": test_password},
        format="json",
    )
    refresh_token = login_res.json()["data"]["refresh"]

    refresh_res = api_client.post(
        "/api/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )
    assert refresh_res.status_code == 200
    assert refresh_res.json().get("success") is True
    assert "access" in refresh_res.json() or "access" in refresh_res.json().get("data", {})
