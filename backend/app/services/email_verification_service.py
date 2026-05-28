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

INVALID_CODE_MESSAGE = "Invalid verification code."
EXPIRED_CODE_MESSAGE = "Verification code has expired."
TOO_MANY_ATTEMPTS_MESSAGE = "Too many verification attempts. Please request a new code."


class EmailVerificationService:
    """
    Service that coordinates domain workflows and business rules.
    """
    def __init__(
        self,
        repository: EmailVerificationRepository | None = None,
        user_repository: UserRepository | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        """
        Initialize the service with optional collaborators and runtime dependencies.
        
        Args:
            repository: The repository value used by this operation.
            user_repository: The user repository value used by this operation.
            email_service: The email service value used by this operation.
        
        Returns:
            None.
        """
        self.settings = get_settings()
        self.repository = repository or EmailVerificationRepository()
        self.user_repository = user_repository or UserRepository()
        self.email_service = email_service or EmailService()

    def normalize_and_validate_email(self, email: str) -> str:
        """
        Normalize and validate email for downstream use.
        
        Args:
            email: Email address used for lookup, verification, or delivery.
        
        Returns:
            Normalized helper result derived from the supplied input.
        
        Raises:
            HTTPException: If request validation, authorization, fraud checks, or rate limits fail.
        """
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
        """
        Is Disposable Domain for the requested operation.
        
        Args:
            email: Email address used for lookup, verification, or delivery.
        
        Returns:
            `True` when the condition is satisfied, otherwise `False`.
        """
        _, _, domain = email.rpartition("@")
        return domain.lower() in _load_disposable_domains(self.settings.DISPOSABLE_EMAIL_DOMAINS_PATH)

    async def create_and_send_code(self, *, user_id: str, email: str) -> dict[str, str]:
        """
        Create and send code for the requested operation.
        
        Args:
            user_id: Unique user identifier used by the operation.
            email: Email address used for lookup, verification, or delivery.
        
        Returns:
            Constructed result for the requested operation.
        """
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
        """
        Verify the submitted code or identity data for the workflow.
        
        Args:
            email: Email address used for lookup, verification, or delivery.
            code: Verification or authorization code supplied by the caller.
        
        Returns:
            None.
        
        Raises:
            _verification_error: If the underlying operation cannot be completed.
        """
        normalized_email = self.normalize_and_validate_email(email)
        verification = await self.repository.find_latest_unconsumed_by_email(normalized_email)
        if verification is None:
            raise self._verification_error(INVALID_CODE_MESSAGE)

        if _as_utc(verification["expires_at"]) <= utc_now():
            await self.repository.mark_expired(verification["_id"])
            raise self._verification_error(EXPIRED_CODE_MESSAGE)

        attempts = int(verification.get("attempts", 0))
        if attempts >= self.settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
            await self.repository.consume(verification["_id"])
            raise self._verification_error(TOO_MANY_ATTEMPTS_MESSAGE)

        if not self.verify_code(code=code, code_hash=str(verification.get("code_hash", ""))):
            consume = attempts + 1 >= self.settings.EMAIL_VERIFICATION_MAX_ATTEMPTS
            await self.repository.increment_attempts(verification["_id"], consume=consume)
            if consume:
                raise self._verification_error(TOO_MANY_ATTEMPTS_MESSAGE)
            raise self._verification_error(INVALID_CODE_MESSAGE)

        user = await self.user_repository.find_by_id(str(verification["user_id"]))
        if user is None:
            await self.repository.consume(verification["_id"])
            raise self._verification_error(INVALID_CODE_MESSAGE)

        await self.user_repository.mark_email_verified(user_id=user["_id"])
        await self.repository.consume(verification["_id"])

    async def resend_verification(self, *, email: str, ignore_cooldown: bool = False) -> None:
        """
        Resend the required verification or notification data.
        
        Args:
            email: Email address used for lookup, verification, or delivery.
            ignore_cooldown: The ignore cooldown value used by this operation.
        
        Returns:
            None.
        """
        normalized_email = self.normalize_and_validate_email(email)
        user = await self.user_repository.find_by_email(normalized_email)
        if user is None or self.is_user_verified(user):
            return

        latest = await self.repository.find_latest_by_email(normalized_email)
        if latest is not None and not ignore_cooldown:
            seconds_since_last = (utc_now() - _as_utc(latest["created_at"])).total_seconds()
            if seconds_since_last < self.settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS:
                return

        await self.create_and_send_code(user_id=user["_id"], email=normalized_email)

    def generate_code(self) -> str:
        """
        Generate Code for the requested operation.
        
        Returns:
            Operation result represented as `str`.
        """
        return f"{secrets.randbelow(1_000_000):06d}"

    def hash_code(self, code: str) -> str:
        """
        Hash code for secure comparison or storage.
        
        Args:
            code: Verification or authorization code supplied by the caller.
        
        Returns:
            Normalized helper result derived from the supplied input.
        """
        secret = self.settings.JWT_SECRET_KEY.encode("utf-8")
        return hmac.digest(secret, code.encode("utf-8"), "sha256").hex()

    def verify_code(self, *, code: str, code_hash: str) -> bool:
        """
        Verify the submitted code or identity data for the workflow.
        
        Args:
            code: Verification or authorization code supplied by the caller.
            code_hash: Hash value representing code.
        
        Returns:
            Outcome of the requested operation.
        """
        if not code or len(code) != 6 or not code.isdigit():
            return False
        return hmac.compare_digest(self.hash_code(code), code_hash)

    def is_user_verified(self, user: dict) -> bool:
        """
        Is User Verified for the requested operation.
        
        Args:
            user: User record involved in the operation.
        
        Returns:
            `True` when the condition is satisfied, otherwise `False`.
        """
        return bool(user.get("email_verified", user.get("is_verified", False)))

    def _verification_error(self, message: str) -> HTTPException:
        """
        Verification Error for the requested operation.
        
        Args:
            message: The message value used by this operation.
        
        Returns:
            Operation result represented as `HTTPException`.
        """
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )


@lru_cache(maxsize=1)
def _load_disposable_domains(configured_path: str) -> set[str]:
    """
    Load Disposable Domains for the requested operation.
    
    Args:
        configured_path: The configured path value used by this operation.
    
    Returns:
        Operation result represented as `set[str]`.
    """
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
    """
    As Utc for the requested operation.
    
    Args:
        value: Value processed by the helper.
    
    Returns:
        Operation result represented as `datetime`.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
