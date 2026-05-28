"""Tests for application startup across supported environments."""

import asyncio
from importlib import reload

import app.main as app_main
from app.config import get_settings


def _patch_lifespan_dependencies(monkeypatch, module) -> None:
    """Replace external infrastructure calls with no-op async functions."""

    async def _noop() -> None:
        return None

    for name in (
        "connect_to_mongo",
        "close_mongo_connection",
        "connect_to_redis",
        "close_redis_connection",
        "ensure_visitor_indexes",
        "ensure_anonymous_ip_usage_indexes",
        "ensure_pdf_indexes",
        "ensure_user_indexes",
        "ensure_refresh_token_indexes",
        "ensure_email_verification_indexes",
        "ensure_user_usage_indexes",
        "ensure_fraud_indexes",
        "ensure_fraud_event_indexes",
        "ensure_identity_link_indexes",
        "ensure_risk_indexes",
        "ensure_behavior_indexes",
        "ensure_fraud_engine_indexes",
        "ensure_admin_audit_indexes",
        "seed_default_admin",
    ):
        monkeypatch.setattr(module, name, _noop)


def _load_app(monkeypatch, **env: str):
    """Reload the app module with the supplied environment variables."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    module = reload(app_main)
    _patch_lifespan_dependencies(monkeypatch, module)
    return module.create_app()


def _run_lifespan(app) -> None:
    """Enter and exit the FastAPI lifespan for startup verification."""

    async def _main() -> None:
        context = app.router.lifespan_context(app)
        await context.__aenter__()
        await context.__aexit__(None, None, None)

    asyncio.run(_main())


def test_app_starts_with_local_settings(monkeypatch) -> None:
    """Ensure the app lifespan enters successfully in local mode."""
    app = _load_app(monkeypatch, APP_ENV="local")

    _run_lifespan(app)

    assert app.title == "PDFCraft"
    assert app.docs_url == "/docs"


def test_app_starts_with_dev_settings(monkeypatch) -> None:
    """Ensure the app lifespan enters successfully in dev mode."""
    app = _load_app(
        monkeypatch,
        APP_ENV="dev",
        FRONTEND_URL="https://dev.example.com",
        ADMIN_FRONTEND_URL="https://admin-dev.example.com",
        BACKEND_PUBLIC_URL="https://api-dev.example.com",
        CORS_ORIGINS='["https://dev.example.com","https://admin-dev.example.com"]',
        MONGODB_URL="mongodb://dev-mongo.internal:27017",
        MONGODB_DB_NAME="fraud_pdf",
        REDIS_URL="redis://dev-redis.internal:6379/0",
        JWT_SECRET_KEY="dev-secret-value-that-is-long-enough",
        ADMIN_API_KEY="dev-admin-key-that-is-long-enough",
        ENABLE_DEFAULT_ADMIN_SEED="false",
    )

    _run_lifespan(app)

    assert any(route.path == "/api/v1/public/config" for route in app.routes)


def test_app_starts_with_production_settings(monkeypatch) -> None:
    """Ensure the app lifespan enters successfully in production mode."""
    app = _load_app(
        monkeypatch,
        APP_ENV="production",
        FRONTEND_URL="https://pdfcraft.example.com",
        ADMIN_FRONTEND_URL="https://admin.pdfcraft.example.com",
        BACKEND_PUBLIC_URL="https://api.pdfcraft.example.com",
        CORS_ORIGINS='["https://pdfcraft.example.com","https://admin.pdfcraft.example.com"]',
        MONGODB_URL="mongodb://prod-mongo.internal:27017",
        MONGODB_DB_NAME="fraud_pdf",
        REDIS_URL="redis://prod-redis.internal:6379/0",
        JWT_SECRET_KEY="prod-secret-value-that-is-long-enough",
        ADMIN_API_KEY="prod-admin-key-that-is-long-enough",
        ENABLE_DEFAULT_ADMIN_SEED="false",
        SECURE_COOKIES="true",
    )

    _run_lifespan(app)

    assert app.docs_url is None
