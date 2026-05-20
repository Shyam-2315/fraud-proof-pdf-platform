from fastapi import APIRouter

from app.schemas.public import PublicConfigResponse
from app.services.public_config_service import PublicConfigService

router = APIRouter(prefix="/api/public", tags=["Public"])
public_config_service = PublicConfigService()


@router.get("/config", response_model=PublicConfigResponse)
async def public_config() -> PublicConfigResponse:
    return public_config_service.get_config()
