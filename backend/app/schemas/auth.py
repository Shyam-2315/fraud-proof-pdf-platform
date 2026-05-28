from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from email_validator import EmailNotValidError, validate_email


class UserRegisterRequest(BaseModel):
    """Validated request payload for customer registration."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8)
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """
        Normalize and validate the registration email address.

        Args:
            value: Raw email string submitted by the client.

        Returns:
            Canonical normalized email address.
        """
        return _normalize_email(value)


class UserLoginRequest(BaseModel):
    """Validated request payload for customer login."""

    email: str = Field(min_length=3, max_length=254)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """
        Normalize and validate a login email address.

        Args:
            value: Raw login email string.

        Returns:
            Lowercased email address used for authentication lookups.

        Raises:
            ValueError: If the value does not resemble a valid email address.
        """
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email address.")
        return value


class VerifyEmailRequest(BaseModel):
    """Validated request payload for email verification."""

    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """
        Normalize and validate the verification email address.

        Args:
            value: Raw email string submitted by the client.

        Returns:
            Canonical normalized email address.
        """
        return _normalize_email(value)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        """
        Validate the submitted six-digit verification code.

        Args:
            value: Raw code string submitted by the client.

        Returns:
            Trimmed six-digit verification code.

        Raises:
            ValueError: If the verification code is not exactly six digits.
        """
        normalized = value.strip()
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError("Verification code must be 6 digits.")
        return normalized


class ResendVerificationRequest(BaseModel):
    """Validated request payload for resending a verification code."""

    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """
        Normalize and validate the email address for resending verification.

        Args:
            value: Raw email string submitted by the client.

        Returns:
            Canonical normalized email address.
        """
        return _normalize_email(value)


class RefreshTokenRequest(BaseModel):
    """Validated request payload for access-token refresh."""

    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    """Validated request payload for refresh-token revocation."""

    refresh_token: str | None = None


class UserResponse(BaseModel):
    """Serialized user payload returned by authentication endpoints."""

    id: str
    user_id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    is_active: bool
    is_verified: bool
    created_at: datetime | None = None


class RegisterResponse(BaseModel):
    """Serialized response returned after registration attempts."""

    success: bool = True
    requires_verification: bool = True
    message: str
    email: str


class AuthResponse(BaseModel):
    """Serialized response returned after successful authentication."""

    success: bool = True
    message: str
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshResponse(BaseModel):
    """Serialized response returned after refresh-token exchange."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """Serialized profile payload for the current authenticated user."""

    id: str
    user_id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    is_active: bool


class VerificationResponse(BaseModel):
    """Serialized response returned by email-verification endpoints."""

    success: bool = True
    message: str


def _normalize_email(value: str) -> str:
    """
    Normalize and validate an email address using the email-validator package.

    Args:
        value: Raw email string submitted by the client.

    Returns:
        Canonical normalized email address.

    Raises:
        ValueError: If the value is not a valid email address.
    """
    try:
        validated = validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError("Invalid email address.") from exc
    return validated.normalized.strip().lower()
