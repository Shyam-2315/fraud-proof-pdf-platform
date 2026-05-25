import os
from uuid import uuid4

import httpx
from pymongo import MongoClient

from conftest import TEST_MONGO_DB_NAME, TEST_MONGO_URL


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8025")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-admin-key")
RUN_IP_SEGMENT = uuid4().int % 200 + 1


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.com"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: httpx.Client) -> dict:
    response = client.post(
        "/api/auth/register",
        headers={"X-Forwarded-For": f"203.0.{RUN_IP_SEGMENT}.{uuid4().int % 250 + 1}"},
        json={
            "email": _email("customer"),
            "full_name": "Customer Test",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _identity_headers(ip_suffix: int = 70) -> dict[str, str]:
    return {
        "X-Forwarded-For": f"203.0.{RUN_IP_SEGMENT}.{ip_suffix}",
        "User-Agent": f"PDFCraftAdminVisibility/{uuid4()}",
    }


def _visitor_payload(prefix: str) -> dict:
    return {
        "local_storage_id": f"{prefix}-local",
        "session_id": f"{prefix}-session",
        "fingerprint_hash": f"{prefix}-fingerprint",
        "device_profile_hash": f"{prefix}-device",
        "canvas_hash": f"{prefix}-canvas",
        "webgl_hash": f"{prefix}-webgl",
        "audio_hash": f"{prefix}-audio",
        "device_info": {
            "screen": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux",
        },
        "automation_signals": {
            "webdriver": False,
            "plugins_count": 5,
            "cookies_enabled": True,
            "local_storage_available": True,
            "session_storage_available": True,
        },
    }


def _identify(client: httpx.Client, prefix: str) -> str:
    response = client.post("/api/visitor/identify", json=_visitor_payload(prefix))
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"success", "visitor_id", "message"}
    return body["visitor_id"]


def _generate(client: httpx.Client, title: str) -> dict:
    response = client.post(
        "/api/pdf/generate",
        json={"title": title, "content": f"{title} body"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_access_ml_models_and_fraud_visibility_endpoints() -> None:
    prefix = f"admin-visible-{uuid4()}"

    with httpx.Client(base_url=BASE_URL, timeout=15.0, headers=_identity_headers(71)) as client:
        visitor_id = _identify(client, prefix)
        _generate(client, "Admin visibility PDF")

        admin_headers = {"X-Admin-API-Key": ADMIN_API_KEY}

        models = client.get("/api/admin/ml/models", headers=admin_headers)
        assert models.status_code == 200, models.text
        assert "items" in models.json()

        active_model = client.get("/api/admin/ml/models/active", headers=admin_headers)
        assert active_model.status_code == 200, active_model.text
        assert active_model.json()["success"] is True

        decisions = client.get(
            f"/api/admin/fraud/decisions?visitor_id={visitor_id}",
            headers=admin_headers,
        )
        assert decisions.status_code == 200, decisions.text
        assert decisions.json()["total"] >= 1

        features = client.get(
            f"/api/admin/fraud/features/{visitor_id}",
            headers=admin_headers,
        )
        assert features.status_code == 200, features.text
        assert features.json()["total"] >= 1

        links = client.get(
            f"/api/admin/fraud/identity-links/{visitor_id}",
            headers=admin_headers,
        )
        assert links.status_code == 200, links.text
        assert "items" in links.json()


def test_customer_cannot_access_admin_ml_endpoints() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        customer = _register(client)
        headers = _auth_header(customer["access_token"])

        models = client.get("/api/admin/ml/models", headers=headers)
        assert models.status_code == 403

        active_model = client.get("/api/admin/ml/models/active", headers=headers)
        assert active_model.status_code == 403

        train = client.post(
            "/api/admin/ml/train",
            headers=headers,
            json={"demo": True, "auto_activate": False, "model_type": "random_forest"},
        )
        assert train.status_code == 403


def test_admin_can_label_visitor() -> None:
    prefix = f"admin-label-{uuid4()}"
    mongo = MongoClient(TEST_MONGO_URL)
    db = mongo[TEST_MONGO_DB_NAME]

    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_identity_headers(72)) as client:
        visitor_id = _identify(client, prefix)
        response = client.post(
            "/api/admin/fraud/label",
            headers={"X-Admin-API-Key": ADMIN_API_KEY},
            json={
                "visitor_id": visitor_id,
                "label": 1,
                "notes": "Confirmed bypass attempt",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["success"] is True
        assert body["label"]["visitor_id"] == visitor_id
        assert body["label"]["label"] == 1

    saved = db.fraud_labels.find_one({"visitor_id": visitor_id, "label": 1})
    assert saved is not None
