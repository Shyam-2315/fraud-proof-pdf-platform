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


def _register(client: httpx.Client, email: str | None = None) -> dict:
    response = client.post(
        "/api/auth/register",
        headers={"X-Forwarded-For": f"198.51.{RUN_IP_SEGMENT}.{uuid4().int % 250 + 1}"},
        json={
            "email": email or _email("customer"),
            "full_name": "Customer Test",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_register_login_refresh_logout_and_me() -> None:
    email = _email("auth")
    auth_headers = {"X-Forwarded-For": f"198.51.{RUN_IP_SEGMENT}.{uuid4().int % 250 + 1}"}
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        registered = _register(client, email)
        assert registered["success"] is True
        assert registered["user"]["role"] == "CUSTOMER"
        assert registered["user"]["plan"] == "FREE"
        assert "password_hash" not in str(registered)

        duplicate = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "full_name": "Duplicate",
                "password": "StrongPassword123",
            },
            headers=auth_headers,
        )
        assert duplicate.status_code == 409

        wrong_login = client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassword123"},
            headers=auth_headers,
        )
        assert wrong_login.status_code == 401

        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": "StrongPassword123"},
            headers=auth_headers,
        )
        assert login.status_code == 200
        login_body = login.json()

        me = client.get("/api/auth/me", headers=_auth_header(login_body["access_token"]))
        assert me.status_code == 200
        assert me.json()["email"] == email

        missing_me = client.get("/api/auth/me")
        assert missing_me.status_code == 401

        refreshed = client.post(
            "/api/auth/refresh",
            json={"refresh_token": login_body["refresh_token"]},
        )
        assert refreshed.status_code == 200
        refreshed_body = refreshed.json()
        assert refreshed_body["access_token"]
        assert refreshed_body["refresh_token"]

        logout = client.post(
            "/api/auth/logout",
            json={"refresh_token": refreshed_body["refresh_token"]},
        )
        assert logout.status_code == 200


def test_authenticated_usage_history_and_download_ownership() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        user_a = _register(client, _email("owner"))
        token_a = user_a["access_token"]

        pdf_ids = []
        for index in range(5):
            response = client.post(
                "/api/pdf/generate",
                headers=_auth_header(token_a),
                json={"title": f"Logged In PDF {index}", "content": "PDF body"},
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["plan"] == "FREE"
            assert body["limit"] == 5
            assert body["used"] == index + 1
            pdf_ids.append(body["pdf_id"])

        blocked = client.post(
            "/api/pdf/generate",
            headers=_auth_header(token_a),
            json={"title": "Sixth PDF", "content": "Blocked body"},
        )
        assert blocked.status_code == 403
        assert blocked.json()["message"] == (
            "Monthly PDF limit reached. Please upgrade your plan to continue."
        )
        assert blocked.json()["requires_upgrade"] is True
        assert "FREE_LIMIT_REACHED" not in str(blocked.json())

        history = client.get("/api/pdf/my-history", headers=_auth_header(token_a))
        assert history.status_code == 200
        assert history.json()["total"] == 5

        download = client.get(
            f"/api/pdf/download/{pdf_ids[0]}",
            headers=_auth_header(token_a),
        )
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/pdf")

        user_b = _register(client, _email("other"))
        forbidden = client.get(
            f"/api/pdf/download/{pdf_ids[0]}",
            headers=_auth_header(user_b["access_token"]),
        )
        assert forbidden.status_code == 403


def test_plan_limits_can_be_changed_for_pro_and_business() -> None:
    mongo = MongoClient(TEST_MONGO_URL)
    db = mongo[TEST_MONGO_DB_NAME]
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        user = _register(client, _email("plan"))
        user_id = user["user"]["id"]
        db.users.update_one({"_id": user_id}, {"$set": {"plan": "PRO"}})
        pro = client.post(
            "/api/pdf/generate",
            headers=_auth_header(user["access_token"]),
            json={"title": "Pro PDF", "content": "Pro body"},
        )
        assert pro.status_code == 200
        assert pro.json()["limit"] == 100

        db.users.update_one({"_id": user_id}, {"$set": {"plan": "BUSINESS"}})
        business = client.post(
            "/api/pdf/generate",
            headers=_auth_header(user["access_token"]),
            json={"title": "Business PDF", "content": "Business body"},
        )
        assert business.status_code == 200
        assert business.json()["limit"] == 1000


def test_admin_jwt_api_key_and_customer_rejection() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        customer = _register(client, _email("notadmin"))
        denied = client.get(
            "/api/admin/fraud/summary",
            headers=_auth_header(customer["access_token"]),
        )
        assert denied.status_code == 403
        assert denied.json()["detail"] == "Admin access required"

        key_response = client.get(
            "/api/admin/fraud/summary",
            headers={"X-Admin-API-Key": ADMIN_API_KEY},
        )
        assert key_response.status_code == 200

        admin_login = client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": f"198.51.{RUN_IP_SEGMENT}.{uuid4().int % 250 + 1}"},
            json={
                "email": os.getenv("DEFAULT_ADMIN_EMAIL", "admin@pdfcraft.local"),
                "password": os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminPassword123"),
            },
        )
        assert admin_login.status_code == 200
        assert admin_login.json()["user"]["role"] == "ADMIN"
        jwt_response = client.get(
            "/api/admin/fraud/summary",
            headers=_auth_header(admin_login.json()["access_token"]),
        )
        assert jwt_response.status_code == 200

        missing = client.get("/api/admin/fraud/summary")
        assert missing.status_code == 401
        wrong = client.get(
            "/api/admin/fraud/summary",
            headers={"X-Admin-API-Key": "wrong-key"},
        )
        assert wrong.status_code == 403


def test_validation_and_login_rate_limit() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        invalid_pdf = client.post(
            "/api/pdf/generate",
            json={"title": "x" * 121, "content": "body"},
        )
        assert invalid_pdf.status_code == 422

        email = _email("limit")
        for index in range(6):
            response = client.post(
                "/api/auth/login",
                json={"email": email, "password": "WrongPassword123"},
            )
            if index < 5:
                assert response.status_code == 401
            else:
                assert response.status_code == 429
