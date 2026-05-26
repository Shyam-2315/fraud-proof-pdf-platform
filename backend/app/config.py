import json
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "PDFCraft"
    APP_ENV: str = "development"
    APP_PORT: int = Field(
        default=8025,
        validation_alias=AliasChoices("APP_PORT", "PORT"),
    )
    APP_HOST: str = "0.0.0.0"
    FRONTEND_URL: str = "http://localhost:3025"
    ADMIN_FRONTEND_URL: str = "http://localhost:3035"
    BACKEND_PUBLIC_URL: str = "http://localhost:8025"

    MONGODB_URL: str = Field(
        default="mongodb://mongodb:27017",
        validation_alias=AliasChoices("MONGODB_URL", "MONGO_URL"),
    )
    MONGODB_DB_NAME: str = Field(
        default="fraud_pdf",
        validation_alias=AliasChoices("MONGODB_DB_NAME", "MONGO_DB_NAME"),
    )

    REDIS_URL: str = "redis://redis:6379/0"

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3025",
            "http://127.0.0.1:3025",
            "http://localhost:3035",
            "http://127.0.0.1:3035",
        ]
    )

    JWT_SECRET_KEY: str = "change-me-super-secret"
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
    ADMIN_API_KEY: str = "change-me-admin-key"
    DEFAULT_ADMIN_EMAIL: str | None = "admin@pdfcraft.local"
    DEFAULT_ADMIN_PASSWORD: str | None = "AdminPassword123"
    DEFAULT_ADMIN_NAME: str = "PDFCraft Admin"
    ENABLE_DEFAULT_ADMIN_SEED: bool = True
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
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = self.APP_ENV.lower()
        if env != "production":
            return self

        insecure_secret_values = {
            "change-me-super-secret",
            "change-me-in-production",
        }
        insecure_admin_keys = {
            "change-me-admin-key",
        }
        if self.JWT_SECRET_KEY in insecure_secret_values or len(self.JWT_SECRET_KEY) < 24:
            raise ValueError("JWT_SECRET_KEY must be changed to a strong secret in production")
        if self.ADMIN_API_KEY in insecure_admin_keys or len(self.ADMIN_API_KEY) < 24:
            raise ValueError("ADMIN_API_KEY must be changed to a strong key in production")
        if self.ENABLE_DEFAULT_ADMIN_SEED and self.DEFAULT_ADMIN_PASSWORD == "AdminPassword123":
            raise ValueError(
                "DEFAULT_ADMIN_PASSWORD must be changed or ENABLE_DEFAULT_ADMIN_SEED=false in production"
            )
        if not self.SECURE_COOKIES:
            raise ValueError("SECURE_COOKIES must be true in production")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("Wildcard CORS origins are not allowed in production")
        for field_name in ("FRONTEND_URL", "ADMIN_FRONTEND_URL", "BACKEND_PUBLIC_URL"):
            if not getattr(self, field_name).startswith("https://"):
                raise ValueError(f"{field_name} must use HTTPS in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
