"""Environment-aware settings loader."""

import os
from functools import lru_cache

from app.core.config.base import BaseAppSettings
from app.core.config.dev import DevSettings
from app.core.config.local import LocalSettings
from app.core.config.production import ProductionSettings

ENVIRONMENT_ALIASES = {
    "local": "local",
    "development": "dev",
    "dev": "dev",
    "staging": "dev",
    "prod": "production",
    "production": "production",
}

ENVIRONMENT_SETTINGS = {
    "local": LocalSettings,
    "dev": DevSettings,
    "production": ProductionSettings,
}


def normalize_app_env(app_env: str | None) -> str:
    """Normalize supported environment aliases to canonical names."""
    normalized = (app_env or "local").strip().lower()
    return ENVIRONMENT_ALIASES.get(normalized, normalized)


@lru_cache
def _get_settings_cached(normalized_env: str) -> BaseAppSettings:
    """Load and cache settings for a normalized application environment."""
    settings_class = ENVIRONMENT_SETTINGS.get(normalized_env)
    if settings_class is None:
        supported = ", ".join(sorted(ENVIRONMENT_SETTINGS))
        raise ValueError(f"Unsupported APP_ENV '{normalized_env}'. Supported values: {supported}")
    settings = settings_class(APP_ENV=normalized_env)
    if normalized_env == "production":
        settings.ENABLE_API_DOCS = False
    return settings


def get_settings() -> BaseAppSettings:
    """Load and cache settings for the active application environment."""
    normalized_env = normalize_app_env(os.getenv("APP_ENV"))
    return _get_settings_cached(normalized_env)


def clear_settings_cache() -> None:
    """Clear cached settings so tests can reload environment changes."""
    _get_settings_cached.cache_clear()


get_settings.cache_clear = _get_settings_cached.cache_clear  # type: ignore[attr-defined]


__all__ = [
    "BaseAppSettings",
    "DevSettings",
    "LocalSettings",
    "ProductionSettings",
    "clear_settings_cache",
    "get_settings",
    "normalize_app_env",
]
