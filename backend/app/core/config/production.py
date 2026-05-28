"""Production configuration."""

from pydantic import field_validator

from app.core.config.dev import DevSettings


class ProductionSettings(DevSettings):
    """Settings for production deployments."""

    APP_ENV: str = "production"
    ENABLE_API_DOCS: bool = False
    WEB_CONCURRENCY: int = 2

    @field_validator("ENABLE_API_DOCS", mode="before")
    @classmethod
    def disable_api_docs(cls, _value: object) -> bool:
        """Force API docs off for production regardless of ambient env overrides."""
        return False
