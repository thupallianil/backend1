import pytest

PROTECTED_ENDPOINTS = [
    "/api/auth/me/",
    "/api/invoices/",
    "/api/clients/",
    "/api/vendors/",
    "/api/quotes/",
    "/api/payments/",
    "/api/reports/",
]

@pytest.mark.smoke
@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
def test_unauthenticated_requests_rejected(api_client, endpoint):
    """
    6. Protected APIs: Verify unauthenticated requests to protected endpoints return 401 Unauthorized.
    """
    response = api_client.get(endpoint)
    assert response.status_code == 401, f"Expected 401 Unauthorized for {endpoint}, got {response.status_code}"


@pytest.mark.smoke
@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", [
    "/api/auth/me/",
    "/api/invoices/",
    "/api/clients/",
    "/api/vendors/",
    "/api/quotes/",
    "/api/payments/",
    "/api/reports/",
])
def test_authenticated_admin_can_access_protected_apis(admin_auth_client, endpoint):
    """
    6. Protected APIs: Verify authenticated users with valid Bearer token can access protected endpoints.
    """
    response = admin_auth_client.get(endpoint)
    assert response.status_code == 200, f"Expected 200 OK for authenticated access to {endpoint}, got {response.status_code}"
