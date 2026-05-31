from datetime import datetime

from pydantic import BaseModel


class AdminMonitoringResponse(BaseModel):
    """High-level production monitoring metrics for the admin dashboard."""

    total_users: int
    total_anonymous_visitors: int
    total_pdfs_generated: int
    pdfs_generated_today: int
    blocked_visitors: int
    fraud_decisions_count: int
    mongodb_health: str
    redis_health: str
    storage_health: str
    backend_readiness_status: str
    checks: dict[str, bool | str]


class AdminRequestLogItem(BaseModel):
    """Sanitized request-log row returned to admin observability views."""

    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: str | None = None
    block_reason: str | None = None
    fraud_score: float | None = None
    created_at: datetime


class AdminRequestLogListResponse(BaseModel):
    """Paginated request-log list for admin observability."""

    total: int
    limit: int
    offset: int = 0
    items: list[AdminRequestLogItem]


class AdminFraudDecisionItem(BaseModel):
    """Fraud decision row enriched with safe visitor context."""

    id: str
    visitor_id: str | None = None
    user_id: str | None = None
    ip_address: str | None = None
    fingerprint_hash: str | None = None
    risk_score: float
    risk_level: str
    decision: str
    action_type: str | None = None
    reason: str | None = None
    created_at: datetime


class AdminFraudDecisionListResponse(BaseModel):
    """Paginated fraud decision list for admin review."""

    total: int
    limit: int
    offset: int = 0
    items: list[AdminFraudDecisionItem]


class AdminUserManagementItem(BaseModel):
    """Admin-safe user row with plan and current-period usage details."""

    user_id: str
    email: str
    full_name: str | None = None
    role: str
    plan: str
    is_active: bool
    is_verified: bool
    email_verified: bool
    used: int
    limit: int
    remaining: int
    month_key: str
    billing_period_start: datetime
    billing_period_end: datetime
    linked_visitor_count: int
    created_at: datetime
    last_login_at: datetime | None = None


class AdminUserManagementListResponse(BaseModel):
    """Paginated admin user-management list."""

    total: int
    limit: int
    offset: int = 0
    items: list[AdminUserManagementItem]


class AdminUserActionResponse(BaseModel):
    """Response returned after an admin blocks or unblocks a user."""

    success: bool
    user: AdminUserManagementItem
