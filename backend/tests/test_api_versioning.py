"""Tests for versioned and backward-compatible API route registration."""

from importlib import reload

import app.main as app_main
from app.config import get_settings


def _load_app(monkeypatch):
    """Reload the application module with local settings for route inspection."""
    monkeypatch.setenv("APP_ENV", "local")
    get_settings.cache_clear()
    return reload(app_main).app


def test_v1_and_legacy_routes_are_both_registered(monkeypatch) -> None:
    """Ensure both versioned and legacy API paths are available."""
    app = _load_app(monkeypatch)
    paths = {route.path for route in app.routes}

    assert "/api/v1/auth/login" in paths
    assert "/api/auth/login" in paths
    assert "/api/v1/pdf/generate" in paths
    assert "/api/pdf/generate" in paths
    assert "/api/v1/account/usage" in paths
    assert "/api/account/usage" in paths
    assert "/api/v1/admin/fraud/summary" in paths
    assert "/api/admin/fraud/summary" in paths
    assert "/health" in paths
