from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import field_validator
from email_validator import EmailNotValidError, validate_email


class AdminDashboardResponse(BaseModel):
    total_visitors: int
    total_users: int
    total_pdfs: int
    anonymous_pdfs: int
    authenticated_pdfs: int
    blocked_visitors: int
    high_risk_visitors: int
    total_fraud_events: int
    blocked_entities: int
    conversion_count: int
    conversion_rate_percent: float
    recent_visitors: list[dict[str, Any]]
    recent_users: list[dict[str, Any]]
    recent_pdfs: list[dict[str, Any]]
    recent_fraud_events: list[dict[str, Any]]


class AdminVisitorListItem(BaseModel):
    visitor_id: str
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int
    risk_score: int
    risk_level: str
    is_blocked: bool
    block_reason: str | None
    ip_count: int
    session_count: int
    fingerprint_count: int
    user_agent_count: int
    created_at: datetime
    last_seen_at: datetime


class AdminVisitorDetailResponse(BaseModel):
    visitor_id: str
    cookie_id: str | None
    local_storage_ids: list[str]
    session_ids: list[str]
    fingerprint_hashes: list[str]
    primary_fingerprint_hash: str | None
    ip_addresses: list[str]
    user_agents: list[str]
    device_info: dict[str, Any]
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int
    risk_score: int
    risk_level: str
    is_blocked: bool
    block_reason: str | None
    created_at: datetime
    last_seen_at: datetime
    generated_pdfs: list[dict[str, Any]]
    fraud_events: list[dict[str, Any]]
    linked_users: list[dict[str, Any]]


class AdminUserListItem(BaseModel):
    user_id: str
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    linked_visitor_count: int
    pdf_count: int
    created_at: datetime
    last_login_at: datetime | None


class AdminPDFListItem(BaseModel):
    pdf_id: str
    visitor_id: str | None
    user_id: str | None
    title: str
    file_name: str
    file_path: str
    generation_type: str
    ip_address: str | None
    fingerprint_hash: str | None
    created_at: datetime


class AdminBlockedEntityItem(BaseModel):
    entity_id: str
    entity_type: str
    entity_value: str
    reason: str
    risk_score: int
    is_active: bool
    created_at: datetime
    expires_at: datetime | None


class AdminListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Any]


class AdminSystemHealthResponse(BaseModel):
    status: str
    service: str
    database: str
    redis: str
    collections: dict[str, int]
    ports: dict[str, int]


class AdminEmailStatusResponse(BaseModel):
    provider: str
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username_configured: bool | None = None
    smtp_password_configured: bool | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool | None = None
    smtp_use_ssl: bool | None = None
    smtp_mode: str | None = None
    brevo_api_key_configured: bool | None = None
    brevo_from_email: str | None = None
    brevo_from_name: str | None = None
    delivery_mode: str | None = None
    ready: bool


class AdminEmailTestRequest(BaseModel):
    to: str

    @field_validator("to")
    @classmethod
    def validate_to(cls, value: str) -> str:
        try:
            validated = validate_email(value, check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError("Invalid email address.") from exc
        return validated.normalized.strip().lower()


class AdminEmailTestResponse(BaseModel):
    success: bool = True
    message: str
