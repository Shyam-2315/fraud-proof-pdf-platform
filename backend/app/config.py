"""Backward-compatible access to application settings."""

from app.core.config import (
    BaseAppSettings,
    DevSettings,
    LocalSettings,
    ProductionSettings,
    clear_settings_cache,
    get_settings,
)

Settings = BaseAppSettings

__all__ = [
    "BaseAppSettings",
    "DevSettings",
    "LocalSettings",
    "ProductionSettings",
    "Settings",
    "clear_settings_cache",
    "get_settings",
]
