from fastapi import APIRouter, Request

from app.schemas.behavior import BehaviorEventRequest, BehaviorEventResponse
from app.services.rate_limit_service import RateLimitService, client_ip
from app.services.behavior_service import BehaviorService

router = APIRouter(prefix="/behavior", tags=["Behavior"])
behavior_service = BehaviorService()
rate_limit_service = RateLimitService()


@router.post("/event", response_model=BehaviorEventResponse)
async def record_behavior_event(
    payload: BehaviorEventRequest,
    request: Request,
) -> BehaviorEventResponse:
    """
    Persist a customer behavior telemetry event for fraud analysis.

    Args:
        payload: Validated behavior event payload from the frontend.
        request: Incoming HTTP request used for rate limiting and context.

    Returns:
        Success response after the event is stored.
    """
    await rate_limit_service.check(
        request,
        bucket="behavior_event",
        identifier=client_ip(request),
        rate="120/minute",
    )
    await behavior_service.record_event(request=request, payload=payload)
    return BehaviorEventResponse(success=True)
