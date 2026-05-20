from app.config import get_settings
from app.core.public_config import (
    LOGIN_REQUIRED_MESSAGE,
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
)
from app.schemas.public import PublicConfigResponse


class PublicConfigService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def get_config(self) -> PublicConfigResponse:
        return PublicConfigResponse(
            product_name=PRODUCT_NAME,
            tagline=PRODUCT_TAGLINE,
            free_limit=self.settings.FREE_USAGE_LIMIT,
            login_required_message=LOGIN_REQUIRED_MESSAGE,
        )
