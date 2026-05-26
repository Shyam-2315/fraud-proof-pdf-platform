from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from email_validator import EmailNotValidError, validate_email


class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8)
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email address.")
        return value


class VerifyEmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError("Verification code must be 6 digits.")
        return normalized


class ResendVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserResponse(BaseModel):
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
    success: bool = True
    requires_verification: bool = True
    message: str
    email: str


class AuthResponse(BaseModel):
    success: bool = True
    message: str
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    is_active: bool


class VerificationResponse(BaseModel):
    success: bool = True
    message: str


def _normalize_email(value: str) -> str:
    try:
        validated = validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError("Invalid email address.") from exc
    return validated.normalized.strip().lower()
