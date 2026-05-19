from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FraudEventResponse(BaseModel):
    event_id: str
    visitor_id: str | None
    event_type: str
    severity: str
    risk_points: int
    message: str
    signals: dict[str, Any]
    created_at: datetime


class FraudEventsListResponse(BaseModel):
    total: int
    items: list[FraudEventResponse]


class BlockedEntityResponse(BaseModel):
    entity_id: str
    entity_type: str
    entity_value: str
    reason: str
    risk_score: int
    created_at: datetime
    expires_at: datetime | None
    is_active: bool


class FraudSummaryResponse(BaseModel):
    total_visitors: int
    blocked_visitors: int
    total_fraud_events: int
    high_risk_visitors: int
    blocked_entities: int
    recent_events: list[FraudEventResponse]
