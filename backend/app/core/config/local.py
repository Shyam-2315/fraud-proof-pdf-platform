"""Local development configuration."""

from pydantic import AliasChoices, Field

from app.core.config.base import BaseAppSettings


class LocalSettings(BaseAppSettings):
    """Settings with safe defaults for local development."""

    APP_ENV: str = "local"
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
    CORS_ORIGINS: str = (
        "http://localhost:3025,"
        "http://127.0.0.1:3025,"
        "http://localhost:3035,"
        "http://127.0.0.1:3035"
    )
    JWT_SECRET_KEY: str = "change-me-super-secret"
    ADMIN_API_KEY: str = "change-me-admin-key"
    DEFAULT_ADMIN_EMAIL: str | None = "admin@pdfcraft.local"
    DEFAULT_ADMIN_PASSWORD: str | None = "AdminPassword123"
    ENABLE_DEFAULT_ADMIN_SEED: bool = True
    SECURE_COOKIES: bool = False
    TRUST_PROXY_HEADERS: bool = False
    ENABLE_API_DOCS: bool = True
