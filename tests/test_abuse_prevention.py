import os
from uuid import uuid4

import httpx


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8025")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-admin-key")

CUSTOMER_FORBIDDEN = {
    "risk_score",
    "risk_level",
    "fingerprint_hash",
    "ip_address",
    "user_agent",
    "fraud_events",
    "block_reason",
    "CRITICAL_RISK",
}


def payload(prefix: str, session: str | None = None) -> dict:
    return {
        "local_storage_id": f"{prefix}-local",
        "session_id": session or f"{prefix}-session",
        "fingerprint_hash": f"{prefix}-fp",
        "device_profile_hash": f"{prefix}-device",
        "canvas_hash": f"{prefix}-canvas",
        "webgl_hash": f"{prefix}-webgl",
        "audio_hash": f"{prefix}-audio",
        "device_info": {
            "screen": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "touch_support": 0,
        },
        "automation_signals": {
            "webdriver": False,
            "plugins_count": 5,
            "cookies_enabled": True,
            "local_storage_available": True,
            "session_storage_available": True,
        },
    }


def assert_customer_safe(body: dict) -> None:
    serialized = str(body)
    for field in CUSTOMER_FORBIDDEN:
        assert field not in body
        assert field not in serialized


def identify(client: httpx.Client, prefix: str, session: str | None = None) -> dict:
    response = client.post("/api/visitor/identify", json=payload(prefix, session))
    assert response.status_code == 200, response.text
    body = response.json()
    assert_customer_safe(body)
    return body


def behavior(client: httpx.Client, event_type: str) -> None:
    client.post("/api/behavior/event", json={"event_type": event_type, "metadata": {}})


def generate(client: httpx.Client, title: str) -> httpx.Response:
    behavior(client, "GENERATE_CLICKED")
    return client.post(
        "/api/pdf/generate",
        json={"title": title, "content": f"{title} body"},
    )


def test_same_fingerprint_new_cookie_keeps_usage_and_links_identity() -> None:
    prefix = f"identity-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as first:
        first_identify = identify(first, prefix)
        behavior(first, "PAGE_VIEW")
        generated = generate(first, "Linked usage PDF")
        assert generated.status_code == 200, generated.text
        assert generated.json()["used"] == 1

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as second:
        second_identify = identify(second, prefix, session=f"{prefix}-session-new")
        assert second_identify["visitor_id"] == first_identify["visitor_id"]
        status = second.get("/api/visitor/status")
        assert status.status_code == 200
        assert status.json()["free_usage_count"] == 1
        assert status.json()["remaining_free_uses"] == 1
        assert_customer_safe(status.json())

    admin = httpx.get(
        f"{BASE_URL}/api/admin/fraud/visitor/{first_identify['visitor_id']}",
        headers={"X-Admin-API-Key": ADMIN_API_KEY},
        timeout=10.0,
    )
    assert admin.status_code == 200
    assert admin.json()["identity_graph_links"]


def test_risky_ip_blocks_anonymous_without_customer_risk_fields() -> None:
    prefix = f"vpn-{uuid4()}"
    headers = {"X-Forwarded-For": "203.0.113.66"}
    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=headers) as client:
        body = identify(client, prefix)
        blocked = client.post(
            "/api/pdf/generate",
            json={"title": "Risky IP", "content": "Risky IP body"},
        )
        assert blocked.status_code == 403
        assert blocked.json()["message"] == (
            "We could not process this request right now. Please try again later."
        )
        assert_customer_safe(blocked.json())

    events = httpx.get(
        f"{BASE_URL}/api/admin/fraud/events",
        params={"visitor_id": body["visitor_id"], "limit": 100},
        headers={"X-Admin-API-Key": ADMIN_API_KEY},
        timeout=10.0,
    )
    assert events.status_code == 200
    event_types = {event["event_type"] for event in events.json()["items"]}
    assert "VPN_PROXY_DETECTED" in event_types
    assert "RISK_SCORE_UPDATED" in event_types


def test_logged_in_generation_works_after_anonymous_limit() -> None:
    prefix = f"login-after-limit-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        identify(client, prefix)
        behavior(client, "PAGE_VIEW")
        assert generate(client, "Anon one").status_code == 200
        assert generate(client, "Anon two").status_code == 200
        third = generate(client, "Anon three")
        assert third.status_code == 403
        assert third.json()["requires_login"] is True

        registered = client.post(
            "/api/auth/register",
            json={
                "email": f"{uuid4()}@example.com",
                "full_name": "Linked User",
                "password": "StrongPassword123",
            },
        )
        assert registered.status_code == 200, registered.text
        token = registered.json()["access_token"]
        authed = client.post(
            "/api/pdf/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Authenticated PDF", "content": "Authenticated body"},
        )
        assert authed.status_code == 200, authed.text
        assert authed.json()["plan"] == "FREE"
