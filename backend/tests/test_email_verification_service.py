import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.services.email_verification_service import EmailVerificationService
from conftest import apply_test_env


class _FakeEmailVerificationRepository:
    def __init__(self) -> None:
        self.documents: list[dict] = []

    async def create_verification(self, document: dict) -> dict:
        self.documents.append(document.copy())
        return document

    async def find_latest_by_email(self, email: str) -> dict | None:
        matches = [doc for doc in self.documents if doc["email"] == email]
        if not matches:
            return None
        return max(matches, key=lambda item: item["created_at"]).copy()

    async def find_latest_unconsumed_by_email(self, email: str) -> dict | None:
        matches = [doc for doc in self.documents if doc["email"] == email and not doc["consumed"]]
        if not matches:
            return None
        return max(matches, key=lambda item: item["created_at"]).copy()

    async def consume_all_for_email(self, email: str) -> None:
        for document in self.documents:
            if document["email"] == email and not document["consumed"]:
                document["consumed"] = True
                document["updated_at"] = datetime.now(UTC)

    async def increment_attempts(self, verification_id: str, consume: bool = False) -> dict | None:
        for document in self.documents:
            if document["_id"] == verification_id:
                document["attempts"] += 1
                document["updated_at"] = datetime.now(UTC)
                if consume:
                    document["consumed"] = True
                return document.copy()
        return None

    async def consume(self, verification_id: str) -> dict | None:
        for document in self.documents:
            if document["_id"] == verification_id:
                document["consumed"] = True
                document["updated_at"] = datetime.now(UTC)
                return document.copy()
        return None

    async def mark_expired(self, verification_id: str) -> dict | None:
        return await self.consume(verification_id)


class _FakeUserRepository:
    def __init__(self, users: list[dict]) -> None:
        self.users = {user["_id"]: user.copy() for user in users}

    async def find_by_id(self, user_id: str) -> dict | None:
        user = self.users.get(user_id)
        return user.copy() if user else None

    async def find_by_email(self, email: str) -> dict | None:
        for user in self.users.values():
            if user["email"] == email:
                return user.copy()
        return None

    async def mark_email_verified(self, user_id: str) -> dict | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        user["email_verified"] = True
        user["email_verified_at"] = datetime.now(UTC)
        user["is_verified"] = True
        return user.copy()


class _FakeEmailService:
    def __init__(self) -> None:
        self.sent_codes: list[tuple[str, str]] = []

    async def send_verification_code(self, *, email: str, code: str) -> None:
        self.sent_codes.append((email, code))


def _build_service(monkeypatch, users: list[dict]) -> tuple[EmailVerificationService, _FakeEmailVerificationRepository, _FakeUserRepository, _FakeEmailService]:
    apply_test_env(
        monkeypatch,
        ENABLE_DISPOSABLE_EMAIL_BLOCK="true",
        ENABLE_EMAIL_MX_CHECK="false",
        EMAIL_VERIFICATION_MAX_ATTEMPTS="5",
        EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS="60",
    )
    verification_repository = _FakeEmailVerificationRepository()
    user_repository = _FakeUserRepository(users)
    email_service = _FakeEmailService()
    service = EmailVerificationService(
        repository=verification_repository,
        user_repository=user_repository,
        email_service=email_service,
    )
    return service, verification_repository, user_repository, email_service


def test_verify_email_with_correct_otp_sets_user_verified(monkeypatch) -> None:
    user = {"_id": "user-1", "email": "user@example.com", "email_verified": False, "is_verified": False}
    service, repository, user_repository, email_service = _build_service(monkeypatch, [user])

    asyncio.run(service.create_and_send_code(user_id=user["_id"], email=user["email"]))
    sent_email, sent_code = email_service.sent_codes[-1]
    assert sent_email == user["email"]

    asyncio.run(service.verify_email(email=user["email"], code=sent_code))

    assert user_repository.users[user["_id"]]["email_verified"] is True
    assert repository.documents[-1]["consumed"] is True


def test_wrong_otp_increments_attempts(monkeypatch) -> None:
    user = {"_id": "user-2", "email": "wrong@example.com", "email_verified": False, "is_verified": False}
    service, repository, _, _ = _build_service(monkeypatch, [user])

    asyncio.run(service.create_and_send_code(user_id=user["_id"], email=user["email"]))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_email(email=user["email"], code="000000"))

    assert exc_info.value.detail == "Invalid verification code."
    assert repository.documents[-1]["attempts"] == 1
    assert repository.documents[-1]["consumed"] is False


def test_expired_otp_fails(monkeypatch) -> None:
    user = {"_id": "user-3", "email": "expired@example.com", "email_verified": False, "is_verified": False}
    service, repository, _, email_service = _build_service(monkeypatch, [user])

    asyncio.run(service.create_and_send_code(user_id=user["_id"], email=user["email"]))
    sent_code = email_service.sent_codes[-1][1]
    repository.documents[-1]["expires_at"] = datetime.now(UTC) - timedelta(minutes=1)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_email(email=user["email"], code=sent_code))

    assert exc_info.value.detail == "Verification code has expired."
    assert repository.documents[-1]["consumed"] is True


def test_consumed_otp_cannot_be_reused(monkeypatch) -> None:
    user = {"_id": "user-4", "email": "used@example.com", "email_verified": False, "is_verified": False}
    service, repository, _, email_service = _build_service(monkeypatch, [user])

    asyncio.run(service.create_and_send_code(user_id=user["_id"], email=user["email"]))
    sent_code = email_service.sent_codes[-1][1]
    asyncio.run(service.verify_email(email=user["email"], code=sent_code))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_email(email=user["email"], code=sent_code))

    assert exc_info.value.detail == "Invalid verification code."
    assert repository.documents[-1]["consumed"] is True


def test_resend_creates_new_otp_for_existing_unverified_user(monkeypatch) -> None:
    user = {"_id": "user-5", "email": "resend@example.com", "email_verified": False, "is_verified": False}
    service, repository, _, email_service = _build_service(monkeypatch, [user])

    asyncio.run(service.create_and_send_code(user_id=user["_id"], email=user["email"]))
    repository.documents[-1]["created_at"] = datetime.now(UTC) - timedelta(seconds=61)
    asyncio.run(service.resend_verification(email=user["email"]))

    assert len(repository.documents) == 2
    assert len(email_service.sent_codes) == 2
    assert repository.documents[0]["consumed"] is True
    assert repository.documents[1]["consumed"] is False


def test_resend_for_unknown_email_does_not_raise(monkeypatch) -> None:
    service, repository, _, email_service = _build_service(monkeypatch, [])

    asyncio.run(service.resend_verification(email="missing@example.com"))

    assert repository.documents == []
    assert email_service.sent_codes == []


def test_wrong_otp_max_attempts_consumes_code(monkeypatch) -> None:
    user = {"_id": "user-6", "email": "attempts@example.com", "email_verified": False, "is_verified": False}
    service, repository, _, _ = _build_service(monkeypatch, [user])

    asyncio.run(service.create_and_send_code(user_id=user["_id"], email=user["email"]))
    repository.documents[-1]["attempts"] = 4

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.verify_email(email=user["email"], code="000000"))

    assert exc_info.value.detail == "Too many verification attempts. Please request a new code."
    assert repository.documents[-1]["attempts"] == 5
    assert repository.documents[-1]["consumed"] is True


def test_disposable_domain_is_rejected_when_block_enabled(monkeypatch) -> None:
    service, _, _, _ = _build_service(monkeypatch, [])

    with pytest.raises(HTTPException) as exc_info:
        service.normalize_and_validate_email("person@mailinator.com")
    assert exc_info.value.detail == "Please use a different email address."
