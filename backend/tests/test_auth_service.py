import asyncio
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException, Request

from app.schemas.auth import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService


class _FakeUserRepository:
    def __init__(self, users: list[dict] | None = None) -> None:
        self.users_by_id = {user["_id"]: user.copy() for user in users or []}

    async def find_by_email(self, email: str) -> dict | None:
        for user in self.users_by_id.values():
            if user["email"] == email:
                return user.copy()
        return None

    async def create_user(self, user_data: dict) -> dict:
        self.users_by_id[user_data["_id"]] = user_data.copy()
        return user_data

    async def update_last_login(self, user_id: str) -> dict | None:
        user = self.users_by_id.get(user_id)
        if user is None:
            return None
        updated = user.copy()
        updated["last_login_at"] = datetime.now(UTC)
        self.users_by_id[user_id] = updated
        return updated.copy()


class _FakeVisitorRepository:
    async def find_by_cookie_id(self, _cookie_id: str | None) -> None:
        return None


class _FakeEmailVerificationService:
    def __init__(self) -> None:
        self.sent_codes: list[tuple[str, str]] = []

    def normalize_and_validate_email(self, email: str) -> str:
        return email.strip().lower()

    async def create_and_send_code(self, *, user_id: str, email: str) -> dict[str, str]:
        self.sent_codes.append((user_id, email))
        return {"email": email}


class _FakeTokenService:
    async def create_token_pair(self, _user: dict) -> tuple[str, str]:
        return ("access-token", "refresh-token")


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/register",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


def _build_service(users: list[dict] | None = None) -> tuple[AuthService, _FakeUserRepository, _FakeEmailVerificationService]:
    user_repository = _FakeUserRepository(users)
    email_verification_service = _FakeEmailVerificationService()
    service = AuthService(
        user_repository=user_repository,
        visitor_repository=_FakeVisitorRepository(),
        token_service=_FakeTokenService(),
        email_verification_service=email_verification_service,
    )
    return service, user_repository, email_verification_service


def test_register_new_email_creates_unverified_user_and_sends_otp() -> None:
    service, user_repository, email_verification_service = _build_service()

    response = asyncio.run(
        service.register_user(
            payload=UserRegisterRequest(
                email="new@example.com",
                full_name="New User",
                password="StrongPassword123",
            ),
            request=_build_request(),
        )
    )

    created_user = next(iter(user_repository.users_by_id.values()))
    assert response.success is True
    assert response.requires_verification is True
    assert response.message == "Account created. Please verify your email."
    assert created_user["email_verified"] is False
    assert created_user["is_verified"] is False
    assert email_verification_service.sent_codes == [(created_user["_id"], "new@example.com")]


def test_register_existing_unverified_email_resends_code() -> None:
    existing_user = {
        "_id": "user-1",
        "email": "pending@example.com",
        "password_hash": "hashed",
        "full_name": "Pending User",
        "role": "CUSTOMER",
        "plan": "FREE",
        "is_active": True,
        "is_verified": False,
        "email_verified": False,
    }
    service, _, email_verification_service = _build_service([existing_user])

    response = asyncio.run(
        service.register_user(
            payload=UserRegisterRequest(
                email="pending@example.com",
                full_name="Pending User",
                password="StrongPassword123",
            ),
            request=_build_request(),
        )
    )

    assert response.success is True
    assert response.requires_verification is True
    assert response.message == "This email is already registered but not verified. We sent a new verification code."
    assert email_verification_service.sent_codes == [("user-1", "pending@example.com")]


def test_register_existing_verified_email_returns_409() -> None:
    existing_user = {
        "_id": "user-2",
        "email": "verified@example.com",
        "password_hash": "hashed",
        "full_name": "Verified User",
        "role": "CUSTOMER",
        "plan": "FREE",
        "is_active": True,
        "is_verified": True,
        "email_verified": True,
    }
    service, _, _ = _build_service([existing_user])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            service.register_user(
                payload=UserRegisterRequest(
                    email="verified@example.com",
                    full_name="Verified User",
                    password="StrongPassword123",
                ),
                request=_build_request(),
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "This email is already registered. Please log in."


def test_login_before_verification_returns_403() -> None:
    existing_user = {
        "_id": "user-3",
        "email": "login-pending@example.com",
        "password_hash": "$2b$12$8j7dJx4A7bQJfF3D4/01zOF9i7YVv5jP8tA3gce9e7cW8eL1lb1X2",
        "full_name": "Login Pending",
        "role": "CUSTOMER",
        "plan": "FREE",
        "is_active": True,
        "is_verified": False,
        "email_verified": False,
    }
    service, user_repository, _ = _build_service([existing_user])

    from app.core.auth import hash_password

    user_repository.users_by_id["user-3"]["password_hash"] = hash_password("StrongPassword123")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            service.login_user(
                payload=UserLoginRequest(
                    email="login-pending@example.com",
                    password="StrongPassword123",
                ),
                request=_build_request(),
            )
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Please verify your email before logging in."
