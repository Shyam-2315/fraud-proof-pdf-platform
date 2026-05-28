"""Development or staging configuration."""

from app.core.config.base import BaseAppSettings


class DevSettings(BaseAppSettings):
    """Settings for shared development and staging environments."""

    APP_ENV: str = "dev"
    SECURE_COOKIES: bool = True
    TRUST_PROXY_HEADERS: bool = True
    ENABLE_API_DOCS: bool = True
    ENABLE_DEFAULT_ADMIN_SEED: bool = False
