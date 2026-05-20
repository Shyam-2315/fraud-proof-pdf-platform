from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FraudEventItem(BaseModel):
    id: str
    visitor_id: str | None
    event_type: str
    severity: str
    action: str
    allowed: bool
    reason: str | None
    risk_score: int
    risk_level: str
    fingerprint_hash: str | None
    local_storage_id: str | None
    session_id: str | None
    cookie_id: str | None
    ip_address: str | None
    user_agent: str | None
    metadata: dict[str, Any]
    created_at: datetime


class FraudEventListResponse(BaseModel):
    total: int
    limit: int
    items: list[FraudEventItem]


class AdminFraudVisitorItem(BaseModel):
    visitor_id: str
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int
    risk_score: int
    risk_level: str
    is_blocked: bool
    block_reason: str | None
    local_storage_id_count: int
    session_id_count: int
    fingerprint_hash_count: int
    ip_address_count: int
    user_agent_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class AdminFraudVisitorsResponse(BaseModel):
    total: int
    limit: int
    items: list[AdminFraudVisitorItem]


class AdminFraudSummaryResponse(BaseModel):
    total_visitors: int
    blocked_visitors: int
    total_generated_pdfs: int
    total_fraud_events: int
    allowed_pdf_generations: int
    blocked_pdf_generations: int
    high_risk_visitors: int
    medium_risk_visitors: int
    low_risk_visitors: int


class AdminPDFItem(BaseModel):
    pdf_id: str
    visitor_id: str | None
    title: str
    file_name: str
    file_path: str
    generation_type: str
    fingerprint_hash: str | None
    ip_address: str | None
    created_at: datetime


class AdminPDFListResponse(BaseModel):
    total: int
    limit: int
    items: list[AdminPDFItem]


class TimelineItem(BaseModel):
    id: str
    item_type: str
    title: str
    metadata: dict[str, Any]
    created_at: datetime


class AdminVisitorInvestigationResponse(BaseModel):
    visitor: dict[str, Any]
    generated_pdfs: list[AdminPDFItem]
    fraud_events: list[FraudEventItem]
    timeline: list[TimelineItem]


class AdminAuditLogItem(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: str | None
    metadata: dict[str, Any]
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    total: int
    limit: int
    items: list[AdminAuditLogItem]
