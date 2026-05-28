"""Base configuration objects shared across environments."""

import json
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base application settings loaded from environment variables."""

    APP_NAME: str = "PDFCraft"
    APP_ENV: str = "local"
    APP_PORT: int = Field(
        default=8025,
        validation_alias=AliasChoices("APP_PORT", "PORT"),
    )
    APP_HOST: str = "0.0.0.0"
    FRONTEND_URL: str = ""
    ADMIN_FRONTEND_URL: str = ""
    BACKEND_PUBLIC_URL: str = ""

    MONGODB_URL: str = Field(
        default="",
        validation_alias=AliasChoices("MONGODB_URL", "MONGO_URL"),
    )
    MONGODB_DB_NAME: str = Field(
        default="",
        validation_alias=AliasChoices("MONGODB_DB_NAME", "MONGO_DB_NAME"),
    )
    REDIS_URL: str = ""

    CORS_ORIGINS: list[str] = Field(default_factory=list)

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    EMAIL_PROVIDER: str = "SMTP"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "PDFCraft"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    BREVO_API_KEY: str = ""
    BREVO_FROM_EMAIL: str = ""
    BREVO_FROM_NAME: str = "PDFCraft"

    EMAIL_VERIFICATION_OTP_TTL_MINUTES: int = 10
    EMAIL_VERIFICATION_MAX_ATTEMPTS: int = 5
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60
    ENABLE_DISPOSABLE_EMAIL_BLOCK: bool = True
    ENABLE_EMAIL_MX_CHECK: bool = False
    DISPOSABLE_EMAIL_DOMAINS_PATH: str = "data/disposable_email_domains.txt"

    FREE_USAGE_LIMIT: int = 2
    ENABLE_SHARED_IP_ANON_QUOTA: bool = True
    ANON_SHARED_IP_FREE_LIMIT: int = 2
    ANON_IP_USAGE_WINDOW_HOURS: int = 24

    ADMIN_API_KEY: str = ""
    DEFAULT_ADMIN_EMAIL: str | None = None
    DEFAULT_ADMIN_PASSWORD: str | None = None
    DEFAULT_ADMIN_NAME: str = "PDFCraft Admin"
    ENABLE_DEFAULT_ADMIN_SEED: bool = False

    PDF_STORAGE_DIR: str = "storage/generated_pdfs"
    SECURE_COOKIES: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None
    TRUST_PROXY_HEADERS: bool = False
    TRUSTED_PROXY_IPS: str = ""

    ENABLE_IP_INTELLIGENCE: bool = False
    IP_INTELLIGENCE_PROVIDER: str = "LOCAL"
    IP_INTELLIGENCE_API_KEY: str | None = None
    MAXMIND_ACCOUNT_ID: str | None = None
    MAXMIND_LICENSE_KEY: str | None = None
    IP_RISK_LIST_PATH: str = "data/ip_risk_list.json"

    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = True

    RATE_LIMIT_ENABLED: bool = True
    VISITOR_IDENTIFY_RATE_LIMIT: str = "30/minute"
    VISITOR_STATUS_RATE_LIMIT: str = "60/minute"
    PDF_GENERATE_RATE_LIMIT: str = "5/minute"
    AUTHENTICATED_PDF_GENERATE_RATE_LIMIT: str = "60/minute"
    AUTH_LOGIN_RATE_LIMIT: str = "5/minute"
    AUTH_REGISTER_RATE_LIMIT: str = "3/hour"
    AUTH_VERIFY_EMAIL_RATE_LIMIT: str = "10/minute"
    AUTH_RESEND_VERIFICATION_RATE_LIMIT: str = "5/minute"
    ADMIN_RATE_LIMIT: str = "120/minute"

    ML_MODELS_DIR: str = "models/fraud"
    ML_AUTO_LOAD_ACTIVE_MODEL: bool = True
    ENABLE_ONLINE_ML_TRAINING: bool = True
    ENABLE_API_DOCS: bool = True
    WEB_CONCURRENCY: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str] | Any:
        """Parse comma-separated or JSON CORS origins into a list."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_FROM_EMAIL",
        "SMTP_FROM_NAME",
        "BREVO_FROM_EMAIL",
        "BREVO_FROM_NAME",
        mode="before",
    )
    @classmethod
    def strip_text_fields(cls, value: Any) -> Any:
        """Trim surrounding whitespace from textual configuration fields."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("EMAIL_PROVIDER", mode="before")
    @classmethod
    def normalize_email_provider(cls, value: Any) -> Any:
        """Normalize the configured email provider name."""
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("SMTP_PASSWORD", mode="before")
    @classmethod
    def normalize_smtp_password(cls, value: Any) -> Any:
        """Remove accidental whitespace inserted into SMTP passwords."""
        if isinstance(value, str):
            return "".join(value.split())
        return value

    @field_validator("BREVO_API_KEY", mode="before")
    @classmethod
    def normalize_brevo_api_key(cls, value: Any) -> Any:
        """Trim the Brevo API key before validation."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        """Ensure the cookie SameSite policy is supported."""
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @model_validator(mode="after")
    def validate_environment_configuration(self) -> "BaseAppSettings":
        """Validate settings that vary by deployment environment."""
        env = self.APP_ENV.lower()

        if env == "local":
            return self

        required_fields = (
            "FRONTEND_URL",
            "ADMIN_FRONTEND_URL",
            "BACKEND_PUBLIC_URL",
            "CORS_ORIGINS",
            "MONGODB_URL",
            "MONGODB_DB_NAME",
            "REDIS_URL",
            "JWT_SECRET_KEY",
            "ADMIN_API_KEY",
        )
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value:
                raise ValueError(f"{field_name} must be set when APP_ENV={env}")

        if self.ENABLE_DEFAULT_ADMIN_SEED and (
            not self.DEFAULT_ADMIN_EMAIL or not self.DEFAULT_ADMIN_PASSWORD
        ):
            raise ValueError(
                "DEFAULT_ADMIN_EMAIL and DEFAULT_ADMIN_PASSWORD are required when "
                "ENABLE_DEFAULT_ADMIN_SEED=true outside local"
            )

        if env != "production":
            return self

        insecure_secret_values = {
            "change-me-super-secret",
            "change-me-in-production",
            "test-secret-value-that-is-long-enough",
        }
        insecure_admin_keys = {
            "change-me-admin-key",
            "test-admin-key-that-is-long-enough",
        }
        if self.JWT_SECRET_KEY in insecure_secret_values or len(self.JWT_SECRET_KEY) < 24:
            raise ValueError("JWT_SECRET_KEY must be changed to a strong secret in production")
        if self.ADMIN_API_KEY in insecure_admin_keys or len(self.ADMIN_API_KEY) < 24:
            raise ValueError("ADMIN_API_KEY must be changed to a strong key in production")
        if self.ENABLE_DEFAULT_ADMIN_SEED:
            raise ValueError("ENABLE_DEFAULT_ADMIN_SEED must be false in production")
        if not self.SECURE_COOKIES:
            raise ValueError("SECURE_COOKIES must be true in production")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("Wildcard CORS origins are not allowed in production")
        for field_name in ("FRONTEND_URL", "ADMIN_FRONTEND_URL", "BACKEND_PUBLIC_URL"):
            if not getattr(self, field_name).startswith("https://"):
                raise ValueError(f"{field_name} must use HTTPS in production")
        return self
