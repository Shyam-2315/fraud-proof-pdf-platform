import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Fraud Proof PDF Platform"
    APP_ENV: str = "development"
    APP_PORT: int = 8025
    FRONTEND_URL: str = "http://localhost:3025"

    MONGO_URL: str = "mongodb://mongodb:27017"
    MONGO_DB_NAME: str = "fraud_proof_pdf"

    REDIS_URL: str = "redis://redis:6379/0"

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3025",
            "http://127.0.0.1:3025",
        ]
    )

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FREE_USAGE_LIMIT: int = 2
    ADMIN_API_KEY: str
    DEFAULT_ADMIN_EMAIL: str | None = None
    DEFAULT_ADMIN_PASSWORD: str | None = None
    DEFAULT_ADMIN_NAME: str = "PDFCraft Admin"
    PDF_STORAGE_DIR: str = "storage/generated_pdfs"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
