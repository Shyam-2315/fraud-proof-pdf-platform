from functools import lru_cache

from app.config import get_settings
from app.core.public_config import (
    LOGIN_REQUIRED_MESSAGE,
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
)
from app.schemas.public import PublicConfigResponse


class PublicConfigService:
    """Return frontend-safe public application configuration."""

    def __init__(self) -> None:
        """Initialize the service with current application settings."""
        self.settings = get_settings()

    def get_config(self) -> PublicConfigResponse:
        """
        Return cached public configuration exposed to the customer frontend.

        Returns:
            Public configuration response safe to return to anonymous clients.
        """
        return _cached_public_config(self.settings.FREE_USAGE_LIMIT)


@lru_cache(maxsize=8)
def _cached_public_config(free_limit: int) -> PublicConfigResponse:
    """
    Build and cache the public configuration response for a free usage limit.

    Args:
        free_limit: Anonymous free usage limit exposed to the frontend.

    Returns:
        Public configuration response object.
    """
    return PublicConfigResponse(
        product_name=PRODUCT_NAME,
        tagline=PRODUCT_TAGLINE,
        free_limit=free_limit,
        login_required_message=LOGIN_REQUIRED_MESSAGE,
    )
