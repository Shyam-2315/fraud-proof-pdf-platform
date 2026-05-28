"""Tests for environment-specific settings loading."""

import pytest

from app.config import DevSettings, LocalSettings, ProductionSettings, get_settings


def _clear_backend_env(monkeypatch) -> None:
    """Remove backend environment variables that influence settings selection."""
    for key in (
        "APP_ENV",
        "FRONTEND_URL",
        "ADMIN_FRONTEND_URL",
        "BACKEND_PUBLIC_URL",
        "CORS_ORIGINS",
        "MONGODB_URL",
        "MONGO_URL",
        "MONGODB_DB_NAME",
        "MONGO_DB_NAME",
        "REDIS_URL",
        "JWT_SECRET_KEY",
        "ADMIN_API_KEY",
        "DEFAULT_ADMIN_EMAIL",
        "DEFAULT_ADMIN_PASSWORD",
        "ENABLE_DEFAULT_ADMIN_SEED",
        "SECURE_COOKIES",
    ):
        monkeypatch.delenv(key, raising=False)


def test_local_settings_use_safe_defaults(monkeypatch) -> None:
    """Ensure local mode falls back to safe developer defaults."""
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "local")
    get_settings.cache_clear()

    settings = get_settings()

    assert isinstance(settings, LocalSettings)
    assert settings.APP_ENV == "local"
    assert settings.MONGODB_URL == "mongodb://mongodb:27017"
    assert settings.REDIS_URL == "redis://redis:6379/0"
    assert settings.JWT_SECRET_KEY == "change-me-super-secret"
    assert settings.ENABLE_DEFAULT_ADMIN_SEED is True


def test_dev_settings_require_explicit_runtime_values(monkeypatch) -> None:
    """Ensure shared dev environments do not fall back to local secrets or URLs."""
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "dev")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="FRONTEND_URL must be set when APP_ENV=dev"):
        get_settings()


def test_production_settings_require_secure_values(monkeypatch) -> None:
    """Ensure production rejects insecure placeholder credentials."""
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://pdfcraft.example.com")
    monkeypatch.setenv("ADMIN_FRONTEND_URL", "https://admin.pdfcraft.example.com")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://api.pdfcraft.example.com")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["https://pdfcraft.example.com","https://admin.pdfcraft.example.com"]',
    )
    monkeypatch.setenv("MONGODB_URL", "mongodb://mongo.internal:27017")
    monkeypatch.setenv("MONGODB_DB_NAME", "fraud_pdf")
    monkeypatch.setenv("REDIS_URL", "redis://redis.internal:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-super-secret")
    monkeypatch.setenv("ADMIN_API_KEY", "change-me-admin-key")
    monkeypatch.setenv("ENABLE_DEFAULT_ADMIN_SEED", "false")
    monkeypatch.setenv("SECURE_COOKIES", "true")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="JWT_SECRET_KEY must be changed"):
        get_settings()


def test_production_settings_load_with_secure_values(monkeypatch) -> None:
    """Ensure production settings load when required secure values are present."""
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://pdfcraft.example.com")
    monkeypatch.setenv("ADMIN_FRONTEND_URL", "https://admin.pdfcraft.example.com")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://api.pdfcraft.example.com")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["https://pdfcraft.example.com","https://admin.pdfcraft.example.com"]',
    )
    monkeypatch.setenv("MONGODB_URL", "mongodb://mongo.internal:27017")
    monkeypatch.setenv("MONGODB_DB_NAME", "fraud_pdf")
    monkeypatch.setenv("REDIS_URL", "redis://redis.internal:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "prod-secret-value-that-is-long-enough")
    monkeypatch.setenv("ADMIN_API_KEY", "prod-admin-key-that-is-long-enough")
    monkeypatch.setenv("ENABLE_DEFAULT_ADMIN_SEED", "false")
    monkeypatch.setenv("SECURE_COOKIES", "true")
    get_settings.cache_clear()

    settings = get_settings()

    assert isinstance(settings, ProductionSettings)
    assert settings.APP_ENV == "production"
    assert settings.ENABLE_API_DOCS is False
    assert settings.SECURE_COOKIES is True


def test_development_alias_maps_to_dev_settings(monkeypatch) -> None:
    """Ensure the legacy development alias still resolves to dev settings."""
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("FRONTEND_URL", "https://dev.example.com")
    monkeypatch.setenv("ADMIN_FRONTEND_URL", "https://admin-dev.example.com")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://api-dev.example.com")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["https://dev.example.com","https://admin-dev.example.com"]',
    )
    monkeypatch.setenv("MONGODB_URL", "mongodb://mongo.internal:27017")
    monkeypatch.setenv("MONGODB_DB_NAME", "fraud_pdf")
    monkeypatch.setenv("REDIS_URL", "redis://redis.internal:6379/0")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-value-that-is-long-enough")
    monkeypatch.setenv("ADMIN_API_KEY", "dev-admin-key-that-is-long-enough")
    monkeypatch.setenv("ENABLE_DEFAULT_ADMIN_SEED", "false")
    monkeypatch.setenv("SECURE_COOKIES", "true")
    get_settings.cache_clear()

    settings = get_settings()

    assert isinstance(settings, DevSettings)
    assert settings.APP_ENV == "dev"
