import pytest
from django.db import connection

@pytest.mark.smoke
@pytest.mark.django_db
def test_backend_database_connection():
    """
    1. Backend health: Verify database connectivity and query execution.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
        row = cursor.fetchone()
    assert row is not None, "Database query returned no rows"
    assert row[0] == 1, f"Expected 1 from database check, got {row[0]}"


@pytest.mark.smoke
@pytest.mark.django_db
def test_backend_public_platform_stats_endpoint(api_client):
    """
    1. Backend health: Verify public platform stats API is reachable and returns valid metrics.
    """
    response = api_client.get("/api/public-stats/")
    assert response.status_code == 200, f"Expected 200 OK from /api/public-stats/, got {response.status_code}"
    
    body = response.json()
    assert body.get("success") is True, "Expected success=True in public stats response"
    assert "data" in body, "Expected 'data' key in public stats response"
    
    data = body["data"]
    assert "total_businesses" in data, "Missing 'total_businesses' metric"
    assert "total_clients" in data, "Missing 'total_clients' metric"
    assert "total_invoices" in data, "Missing 'total_invoices' metric"
    assert "total_volume" in data, "Missing 'total_volume' metric"
    assert data.get("is_live_data") is True, "Expected is_live_data=True"
