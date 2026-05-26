import hmac
import logging
import secrets
from datetime import UTC, datetime
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException, status

from app.config import get_settings
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.utils.security import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class EmailVerificationService:
    def __init__(
        self,
        repository: EmailVerificationRepository | None = None,
        user_repository: UserRepository | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.repository = repository or EmailVerificationRepository()
        self.user_repository = user_repository or UserRepository()
        self.email_service = email_service or EmailService()

    def normalize_and_validate_email(self, email: str) -> str:
        try:
            validated = validate_email(
                email,
                check_deliverability=bool(self.settings.ENABLE_EMAIL_MX_CHECK),
            )
        except EmailNotValidError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please enter a valid email address.",
            ) from exc

        normalized_email = validated.normalized.strip().lower()
        if self.settings.ENABLE_DISPOSABLE_EMAIL_BLOCK and self.is_disposable_domain(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please use a different email address.",
            )
        return normalized_email

    def is_disposable_domain(self, email: str) -> bool:
        _, _, domain = email.rpartition("@")
        return domain.lower() in _load_disposable_domains(self.settings.DISPOSABLE_EMAIL_DOMAINS_PATH)

    async def create_and_send_code(self, *, user_id: str, email: str) -> dict[str, str]:
        code = self.generate_code()
        code_hash = self.hash_code(code)
        now = utc_now()
        await self.repository.consume_all_for_email(email)
        document = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "email": email,
            "code_hash": code_hash,
            "expires_at": now + timedelta(minutes=self.settings.EMAIL_VERIFICATION_OTP_TTL_MINUTES),
            "attempts": 0,
            "consumed": False,
            "created_at": now,
            "updated_at": now,
        }
        await self.repository.create_verification(document)
        await self.email_service.send_verification_code(email=email, code=code)
        return {"email": email}

    async def verify_email(self, *, email: str, code: str) -> None:
        normalized_email = self.normalize_and_validate_email(email)
        verification = await self.repository.find_latest_unconsumed_by_email(normalized_email)
        if verification is None:
            raise self._invalid_code_error()

        if _as_utc(verification["expires_at"]) <= utc_now():
            await self.repository.mark_expired(verification["_id"])
            raise self._invalid_code_error()

        attempts = int(verification.get("attempts", 0))
        if attempts >= self.settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
            await self.repository.consume(verification["_id"])
            raise self._invalid_code_error()

        if not self.verify_code(code=code, code_hash=str(verification.get("code_hash", ""))):
            consume = attempts + 1 >= self.settings.EMAIL_VERIFICATION_MAX_ATTEMPTS
            await self.repository.increment_attempts(verification["_id"], consume=consume)
            raise self._invalid_code_error()

        user = await self.user_repository.find_by_id(str(verification["user_id"]))
        if user is None:
            await self.repository.consume(verification["_id"])
            raise self._invalid_code_error()

        await self.user_repository.mark_email_verified(user_id=user["_id"])
        await self.repository.consume(verification["_id"])

    async def resend_verification(self, *, email: str) -> None:
        normalized_email = self.normalize_and_validate_email(email)
        user = await self.user_repository.find_by_email(normalized_email)
        if user is None or self.is_user_verified(user):
            return

        latest = await self.repository.find_latest_by_email(normalized_email)
        if latest is not None:
            seconds_since_last = (utc_now() - _as_utc(latest["created_at"])).total_seconds()
            if seconds_since_last < self.settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
                return

        await self.create_and_send_code(user_id=user["_id"], email=normalized_email)

    def generate_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def hash_code(self, code: str) -> str:
        secret = self.settings.JWT_SECRET_KEY.encode("utf-8")
        return hmac.digest(secret, code.encode("utf-8"), "sha256").hex()

    def verify_code(self, *, code: str, code_hash: str) -> bool:
        if not code or len(code) != 6 or not code.isdigit():
            return False
        return hmac.compare_digest(self.hash_code(code), code_hash)

    def is_user_verified(self, user: dict) -> bool:
        return bool(user.get("email_verified", user.get("is_verified", False)))

    def _invalid_code_error(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )


@lru_cache(maxsize=1)
def _load_disposable_domains(configured_path: str) -> set[str]:
    path = Path(configured_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    if not path.exists():
        return set()

    try:
        return {
            stripped.lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if (stripped := line.strip()) and not stripped.startswith("#")
        }
    except OSError:
        logger.warning("Failed to read disposable email domain list path=%s", path)
        return set()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
