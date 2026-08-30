import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_public_ai_chatbot_endpoint():
    client = APIClient()

    # 1. Empty query returns helpful guidance & suggestions
    res = client.post("/api/public-ai-chatbot/", {}, format="json")
    assert res.status_code == 400
    assert len(res.json()["suggestions"]) > 0

    # 2. Free Trial inquiry
    res = client.post("/api/public-ai-chatbot/", {"message": "How does the 5-project Free Trial work?"}, format="json")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "Free Trial" in res.json()["reply"]
    assert len(res.json()["suggestions"]) > 0

    # 3. Vendor deliverables inquiry
    res = client.post("/api/public-ai-chatbot/", {"message": "How do vendor deliverables and QA reviews work?"}, format="json")
    assert res.status_code == 200
    assert "Vendor" in res.json()["reply"]
    assert "Deliverable" in res.json()["reply"]

    # 4. Invoices & Razorpay payments inquiry
    res = client.post("/api/public-ai-chatbot/", {"message": "Can clients pay invoices with Razorpay UPI?"}, format="json")
    assert res.status_code == 200
    assert "Razorpay" in res.json()["reply"] or "Invoicing" in res.json()["reply"]

    # 5. Role permissions inquiry
    res = client.post("/api/public-ai-chatbot/", {"message": "What are the 4 user roles?"}, format="json")
    assert res.status_code == 200
    assert "Super Admin" in res.json()["reply"]
    assert "Business Admin" in res.json()["reply"]
