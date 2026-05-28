from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.schemas.subscription import AccountUsageResponse
from app.services.user_usage_service import UserUsageService

router = APIRouter(prefix="/account", tags=["Account"])
usage_service = UserUsageService()


@router.get("/usage", response_model=AccountUsageResponse)
async def account_usage(current_user: dict = Depends(get_current_user)) -> AccountUsageResponse:
    """
    Return the authenticated user's current usage summary.

    Args:
        current_user: Authenticated user loaded from the bearer token.

    Returns:
        Aggregated usage information for the current account.
    """
    usage = await usage_service.get_current_usage(current_user)
    return AccountUsageResponse(**usage)
