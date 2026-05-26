import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from pymongo import MongoClient

from app.core.auth import create_access_token, hash_password
from app.utils.security import generate_uuid
from conftest import TEST_MONGO_DB_NAME, TEST_MONGO_URL


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8025")
RUN_IP_SEGMENT = uuid4().int % 200 + 1


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.com"


def _register(client: httpx.Client, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        headers={"X-Forwarded-For": f"198.18.{RUN_IP_SEGMENT}.{uuid4().int % 250 + 1}"},
        json={
            "email": email,
            "full_name": "Verification Test",
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_resend_verification_returns_generic_response_and_creates_new_otp() -> None:
    email = _email("resend-flow")
    mongo = MongoClient(TEST_MONGO_URL)
    db = mongo[TEST_MONGO_DB_NAME]

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        _register(client, email)
        latest = db.email_verifications.find_one({"email": email}, sort=[("created_at", -1)])
        assert latest is not None
        db.email_verifications.update_one(
            {"_id": latest["_id"]},
            {"$set": {"created_at": datetime.now(UTC) - timedelta(seconds=61)}},
        )

        response = client.post("/api/auth/resend-verification", json={"email": email})
        assert response.status_code == 200, response.text
        assert response.json() == {
            "success": True,
            "message": "If this email is registered, a verification code has been sent.",
        }

        unknown = client.post("/api/auth/resend-verification", json={"email": _email("missing")})
        assert unknown.status_code == 200, unknown.text
        assert unknown.json() == response.json()

    assert db.email_verifications.count_documents({"email": email}) >= 2


def test_disposable_domain_register_is_rejected() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/api/auth/register",
            json={
                "email": f"disposable-{uuid4()}@mailinator.com",
                "full_name": "Disposable Test",
                "password": "StrongPassword123",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Please use a different email address."


def test_unverified_jwt_cannot_generate_logged_in_pdf() -> None:
    mongo = MongoClient(TEST_MONGO_URL)
    db = mongo[TEST_MONGO_DB_NAME]
    user_id = generate_uuid()
    db.users.insert_one(
        {
            "_id": user_id,
            "email": _email("unverified-jwt"),
            "password_hash": hash_password("StrongPassword123"),
            "full_name": "Unverified JWT",
            "role": "CUSTOMER",
            "plan": "FREE",
            "is_active": True,
            "is_verified": False,
            "email_verified": False,
            "email_verified_at": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_login_at": None,
            "linked_visitor_ids": [],
            "fingerprint_hashes": [],
            "device_profile_hashes": [],
            "ip_addresses": [],
        }
    )
    token = create_access_token(subject=user_id, role="CUSTOMER")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/api/pdf/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Blocked PDF", "content": "Blocked content"},
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "Please verify your email to continue."}


def test_verify_email_wrong_code_response_does_not_leak_internal_details() -> None:
    email = _email("verify-wrong")
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        _register(client, email)
        response = client.post(
            "/api/auth/verify-email",
            json={"email": email, "code": "000000"},
        )
        assert response.status_code == 400
        body = response.json()
        assert body == {"detail": "Invalid verification code."}
        serialized = str(body).lower()
        assert "otp" not in serialized
        assert "hash" not in serialized
        assert "internal" not in serialized
