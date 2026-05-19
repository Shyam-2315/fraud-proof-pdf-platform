from fastapi import APIRouter, Query

from app.repositories.fraud_repository import FraudRepository
from app.schemas.fraud import FraudEventsListResponse, FraudSummaryResponse
from app.services.fraud_service import FraudService, build_fraud_event_response

router = APIRouter(prefix="/api/fraud", tags=["Fraud"])
fraud_repository = FraudRepository()
fraud_service = FraudService()


@router.get("/events", response_model=FraudEventsListResponse)
async def list_fraud_events(
    limit: int = Query(default=100, ge=1, le=500),
) -> FraudEventsListResponse:
    events = await fraud_repository.list_fraud_events(limit=limit)
    return FraudEventsListResponse(
        total=len(events),
        items=[build_fraud_event_response(event) for event in events],
    )


@router.get("/summary", response_model=FraudSummaryResponse)
async def fraud_summary() -> FraudSummaryResponse:
    return await fraud_service.get_fraud_summary()
