import pytest

@pytest.mark.smoke
@pytest.mark.django_db
def test_logout_blacklists_refresh_token(api_client, admin_user, test_password):
    """
    7. Logout: Submitting refresh token to logout endpoint blacklists it,
       and subsequent refresh requests with the blacklisted token are rejected.
    """
    # 1. Login to get fresh tokens
    login_res = api_client.post(
        "/api/auth/login/",
        {"email": admin_user.email, "password": test_password},
        format="json",
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["data"]["access"]
    refresh_token = login_res.json()["data"]["refresh"]

    # 2. Authenticated Logout
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    logout_res = api_client.post(
        "/api/auth/logout/",
        {"refresh": refresh_token},
        format="json",
    )
    assert logout_res.status_code == 200
    assert logout_res.json().get("success") is True

    # 3. Verify the blacklisted refresh token CANNOT be used to refresh access tokens
    api_client.credentials()  # clear credentials
    ref_res = api_client.post(
        "/api/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )
    assert ref_res.status_code == 401, (
        f"Expected 401 for blacklisted refresh token, got {ref_res.status_code}"
    )
    assert ref_res.json().get("success") is False
