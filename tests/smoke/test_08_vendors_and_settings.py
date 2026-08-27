import pytest
from rest_framework import status
from api.models import Vendor, AppSettings, BusinessProfile

@pytest.mark.smoke
@pytest.mark.django_db
def test_vendor_full_lifecycle(admin_auth_client, admin_user):
    """
    Test complete Vendor lifecycle:
    1. Create Vendor with GSTIN, PAN, Bank & UPI
    2. Retrieve Vendor List with filtering and search
    3. Retrieve Vendor Details
    4. Update Vendor
    5. Retrieve Vendor Stats
    6. Delete Vendor
    """
    # 1. Create Vendor
    vendor_payload = {
        "name": "Tata Steel Supply Ltd",
        "company_name": "Tata Steel Limited",
        "email": "procurement@tatasteel.com",
        "phone": "+91 9876543210",
        "category": "raw_materials",
        "tax_number": "27AAACT0001A1Z5",
        "pan_number": "AAACT0001A",
        "bank_name": "State Bank of India",
        "account_name": "Tata Steel Operational A/C",
        "account_number": "123456789012",
        "ifsc_code": "SBIN0001234",
        "upi_id": "tatasteel@sbi",
        "payment_terms": "Net 30",
        "address": "Jamshedpur Industrial Area",
        "city": "Jamshedpur",
        "state": "Jharkhand",
        "country": "India",
        "postal_code": "831001",
        "is_active": True,
    }

    create_res = admin_auth_client.post("/api/vendors/", vendor_payload, format="json")
    assert create_res.status_code == status.HTTP_201_CREATED, f"Vendor creation failed: {create_res.content}"
    vendor_data = create_res.json().get("data", {})
    vendor_id = vendor_data.get("id")
    assert vendor_id is not None
    assert vendor_data["name"] == vendor_payload["name"]
    assert vendor_data["tax_number"] == vendor_payload["tax_number"]
    assert vendor_data["upi_id"] == vendor_payload["upi_id"]

    # 2. List Vendors
    list_res = admin_auth_client.get("/api/vendors/")
    assert list_res.status_code == status.HTTP_200_OK
    assert list_res.json().get("success") is True
    assert list_res.json().get("count") >= 1

    # 3. Search Vendor
    search_res = admin_auth_client.get("/api/vendors/?search=Tata")
    assert search_res.status_code == status.HTTP_200_OK
    assert len(search_res.json().get("data", [])) >= 1

    # 4. Filter by Category
    cat_res = admin_auth_client.get("/api/vendors/?category=raw_materials")
    assert cat_res.status_code == status.HTTP_200_OK
    assert len(cat_res.json().get("data", [])) >= 1

    # 5. Vendor Details
    detail_res = admin_auth_client.get(f"/api/vendors/{vendor_id}/")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.json()["data"]["id"] == vendor_id

    # 6. Update Vendor (PATCH)
    update_res = admin_auth_client.patch(
        f"/api/vendors/{vendor_id}/",
        {"payment_terms": "Net 45", "phone": "+91 9998887776"},
        format="json",
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["data"]["payment_terms"] == "Net 45"
    assert update_res.json()["data"]["phone"] == "+91 9998887776"

    # 7. Vendor Stats
    stats_res = admin_auth_client.get("/api/vendors/stats/")
    assert stats_res.status_code == status.HTTP_200_OK
    assert stats_res.json().get("success") is True
    stats_data = stats_res.json().get("data", {})
    assert stats_data.get("total_vendors", 0) >= 1
    assert stats_data.get("active_vendors", 0) >= 1

    # 8. Delete Vendor
    del_res = admin_auth_client.delete(f"/api/vendors/{vendor_id}/")
    assert del_res.status_code == status.HTTP_200_OK
    assert not Vendor.objects.filter(id=vendor_id).exists()


@pytest.mark.smoke
@pytest.mark.django_db
def test_settings_full_lifecycle(admin_auth_client, admin_user):

    """
    Test complete Settings lifecycle:
    1. Retrieve settings object for authenticated business owner
    2. Update General & Business settings
    3. Update Tax & Payment settings
    4. Confirm persistence in database
    """
    # 1. Retrieve current settings
    get_res = admin_auth_client.get("/api/settings/")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json().get("success") is True
    data = get_res.json().get("data", {})
    assert "business" in data
    assert "general" in data
    assert "invoice" in data
    assert "quotation" in data
    assert "tax" in data
    assert "payment" in data

    # 2. Update Settings (PUT / PATCH)
    update_payload = {
        "business": {
            "businessName": "Enterprise Apex Technologies Ltd",
            "legalName": "Enterprise Apex Technologies Private Limited",
            "taxNumber": "27ABCDE1234F1Z5",
            "currency": "INR",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
        },
        "general": {
            "currency": "INR",
            "currencySymbol": "₹",
            "dateFormat": "DD/MM/YYYY",
            "timezone": "Asia/Kolkata",
        },
        "tax": {
            "enabled": True,
            "taxName": "GST",
            "defaultRate": 18,
        },
        "payment": {
            "onlinePayment": True,
            "bankTransfer": True,
            "bankName": "HDFC Bank",
            "accountNumber": "987654321000",
            "ifscCode": "HDFC0001234",
            "upiId": "apextech@hdfcbank",
        },
    }

    put_res = admin_auth_client.put("/api/settings/", update_payload, format="json")
    assert put_res.status_code == status.HTTP_200_OK
    assert put_res.json().get("success") is True

    # 3. Re-fetch and verify updated settings
    verify_res = admin_auth_client.get("/api/settings/")
    assert verify_res.status_code == status.HTTP_200_OK

    v_data = verify_res.json().get("data", {})
    assert v_data["business"]["businessName"] == "Enterprise Apex Technologies Ltd"
    assert v_data["tax"]["taxName"] == "GST"
    assert v_data["payment"]["upiId"] == "apextech@hdfcbank"
