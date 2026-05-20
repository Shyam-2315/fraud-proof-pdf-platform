from fastapi import APIRouter, Request

from app.schemas.behavior import BehaviorEventRequest, BehaviorEventResponse
from app.services.behavior_service import BehaviorService

router = APIRouter(prefix="/api/behavior", tags=["Behavior"])
behavior_service = BehaviorService()


@router.post("/event", response_model=BehaviorEventResponse)
async def record_behavior_event(
    payload: BehaviorEventRequest,
    request: Request,
) -> BehaviorEventResponse:
    await behavior_service.record_event(request=request, payload=payload)
    return BehaviorEventResponse(success=True)
