from fastapi import APIRouter, Response

from app.schemas.public import PublicConfigResponse
from app.services.public_config_service import PublicConfigService

router = APIRouter(prefix="/public", tags=["Public"])
public_config_service = PublicConfigService()


@router.get("/config", response_model=PublicConfigResponse)
async def public_config(response: Response) -> PublicConfigResponse:
    """
    Return frontend-safe public configuration values.

    Args:
        response: Outgoing HTTP response used to attach cache headers.

    Returns:
        Public runtime configuration safe to expose to browsers.
    """
    response.headers["Cache-Control"] = "public, max-age=300"
    return public_config_service.get_config()
