import os
from uuid import uuid4

import httpx
from pymongo import MongoClient


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8025")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-admin-key")
MONGO_URL = os.getenv("TEST_MONGO_URL", "mongodb://localhost:27225")
MONGO_DB_NAME = os.getenv("TEST_MONGO_DB_NAME", "fraud_proof_pdf")

CUSTOMER_FORBIDDEN_FIELDS = {
    "tracked_signals",
    "risk_score",
    "risk_level",
    "fingerprint_hash",
    "fingerprint_hashes",
    "ip_address",
    "ip_addresses",
    "user_agent",
    "user_agents",
    "cookie_id",
    "session_id",
    "session_ids",
    "local_storage_ids",
    "fraud_events",
    "block_reason",
    "FREE_LIMIT_REACHED",
}


def _visitor_payload(prefix: str, session_id: str) -> dict:
    return {
        "local_storage_id": f"{prefix}-local",
        "session_id": session_id,
        "fingerprint_hash": f"{prefix}-fingerprint",
        "device_info": {
            "screen": "1920x1080",
            "timezone": "Asia/Kolkata",
            "language": "en-IN",
            "platform": "Windows",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "touch_support": 0,
        },
    }


def _generate_pdf(client: httpx.Client, title: str, content: str) -> httpx.Response:
    return client.post(
        "/api/pdf/generate",
        json={"title": title, "content": content},
    )


def _assert_customer_safe(body: dict) -> None:
    serialized = str(body)
    for forbidden in CUSTOMER_FORBIDDEN_FIELDS:
        assert forbidden not in body
        assert forbidden not in serialized


def test_public_config_returns_pdfcraft_branding_without_fraud_terms() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.get("/api/public/config")
        assert response.status_code == 200
        body = response.json()
        assert body["product_name"] == "PDFCraft"
        assert body["free_limit"] == 2
        serialized = str(body).lower()
        assert "fraud" not in serialized
        assert "fingerprint" not in serialized
        assert "risk" not in serialized
        assert "tracking" not in serialized


def test_customer_flow_is_pdfcraft_safe_and_admin_is_protected() -> None:
    prefix = f"pdfcraft-test-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        identify = client.post(
            "/api/visitor/identify",
            json=_visitor_payload(prefix, f"{prefix}-session-001"),
        )
        assert identify.status_code == 200
        identify_body = identify.json()
        visitor_id = identify_body["visitor_id"]
        _assert_customer_safe(identify_body)

        status = client.get("/api/visitor/status")
        assert status.status_code == 200
        status_body = status.json()
        assert status_body["remaining_free_uses"] == 2
        assert "free PDF generation" in status_body["message"]
        _assert_customer_safe(status_body)

        first_pdf = _generate_pdf(client, "Customer PDF 1", "First free PDF")
        assert first_pdf.status_code == 200
        first_body = first_pdf.json()
        assert first_body["success"] is True
        assert first_body["title"] == "Customer PDF 1"
        assert first_body["free_limit"] == 2
        assert first_body["used"] == 1
        assert first_body["remaining"] == 1
        _assert_customer_safe(first_body)

        second_pdf = _generate_pdf(client, "Customer PDF 2", "Second free PDF")
        assert second_pdf.status_code == 200
        second_body = second_pdf.json()
        assert second_body["used"] == 2
        assert second_body["remaining"] == 0
        _assert_customer_safe(second_body)

        third_pdf = _generate_pdf(
            client,
            "Customer PDF 3",
            "Third PDF should be blocked",
        )
        assert third_pdf.status_code == 403
        blocked_body = third_pdf.json()
        assert blocked_body == {
            "success": False,
            "message": "Free limit reached. Please log in to continue.",
            "free_limit": 2,
            "used": 2,
            "remaining": 0,
            "requires_login": True,
        }
        _assert_customer_safe(blocked_body)

        blocked_status = client.get("/api/visitor/status")
        assert blocked_status.status_code == 200
        blocked_status_body = blocked_status.json()
        assert blocked_status_body["is_blocked"] is True
        assert blocked_status_body["requires_login"] is True
        assert blocked_status_body["message"] == (
            "Free limit reached. Please log in to continue."
        )
        _assert_customer_safe(blocked_status_body)

        history = client.get("/api/pdf/my-history")
        assert history.status_code == 200
        history_body = history.json()
        assert "visitor_id" not in history_body
        assert history_body["total"] == 2
        assert len(history_body["items"]) == 2
        assert all("download_url" in item for item in history_body["items"])
        _assert_customer_safe(history_body)

        for path in (
            "/api/admin/fraud/summary",
            "/api/admin/fraud/events",
            "/api/admin/fraud/visitors",
            "/api/admin/pdfs",
            "/api/admin/audit-logs",
        ):
            response = client.get(path)
            assert response.status_code == 401
            assert response.json()["detail"] == "Admin API key required"

        events = client.get(
            "/api/admin/fraud/events",
            params={"visitor_id": visitor_id, "limit": 100},
            headers={"X-Admin-API-Key": ADMIN_API_KEY},
        )
        assert events.status_code == 200
        event_types = {item["event_type"] for item in events.json()["items"]}
        assert "VISITOR_IDENTIFIED" in event_types
        assert "PDF_GENERATION_ALLOWED" in event_types
        assert "PDF_GENERATION_BLOCKED" in event_types
        assert "FREE_LIMIT_REACHED" in event_types
        assert "VISITOR_BLOCKED" in event_types


def test_admin_access_and_internal_fields() -> None:
    headers = {"X-Admin-API-Key": ADMIN_API_KEY}
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        invalid = client.get(
            "/api/admin/fraud/summary",
            headers={"X-Admin-API-Key": "wrong-key"},
        )
        assert invalid.status_code == 403
        assert invalid.json()["detail"] == "Invalid admin API key"

        summary = client.get("/api/admin/fraud/summary", headers=headers)
        assert summary.status_code == 200
        assert "total_fraud_events" in summary.json()

        events = client.get("/api/admin/fraud/events", headers=headers)
        assert events.status_code == 200
        if events.json()["items"]:
            event = events.json()["items"][0]
            assert "risk_score" in event
            assert "fingerprint_hash" in event
            assert "ip_address" in event

        visitors = client.get("/api/admin/fraud/visitors", headers=headers)
        assert visitors.status_code == 200
        if visitors.json()["items"]:
            visitor = visitors.json()["items"][0]
            assert "risk_score" in visitor
            assert "local_storage_id_count" in visitor
            assert "fingerprint_hash_count" in visitor

        pdfs = client.get("/api/admin/pdfs", headers=headers)
        assert pdfs.status_code == 200

        audit_logs = client.get("/api/admin/audit-logs", headers=headers)
        assert audit_logs.status_code == 200
        assert "items" in audit_logs.json()


def test_admin_audit_log_created_after_successful_admin_access() -> None:
    mongo = MongoClient(MONGO_URL)
    db = mongo[MONGO_DB_NAME]
    before = db.admin_audit_logs.count_documents(
        {"action": "ADMIN_VIEWED_FRAUD_SUMMARY"}
    )

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.get(
            "/api/admin/fraud/summary",
            headers={"X-Admin-API-Key": ADMIN_API_KEY},
        )
        assert response.status_code == 200

    after = db.admin_audit_logs.count_documents(
        {"action": "ADMIN_VIEWED_FRAUD_SUMMARY"}
    )
    assert after == before + 1
