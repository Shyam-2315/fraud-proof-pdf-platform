from typing import Literal

from fastapi import APIRouter, Query

from app.schemas.admin import (
    AdminDashboardResponse,
    AdminListResponse,
    AdminSystemHealthResponse,
    AdminVisitorDetailResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_service = AdminService()

RiskLevelParam = Literal["LOW", "MEDIUM", "HIGH"]
GenerationTypeParam = Literal["ANONYMOUS", "AUTHENTICATED"]
BlockedEntityTypeParam = Literal[
    "FINGERPRINT",
    "IP",
    "COOKIE",
    "LOCAL_STORAGE",
    "VISITOR",
]


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def dashboard() -> AdminDashboardResponse:
    """
    Return high-level admin dashboard metrics.

    Returns:
        Aggregated dashboard data for the admin console.
    """
    return await admin_service.get_dashboard()


@router.get("/visitors", response_model=AdminListResponse)
async def visitors(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    risk_level: RiskLevelParam | None = None,
    is_blocked: bool | None = None,
) -> AdminListResponse:
    """
    Return paginated visitor records for the admin console.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        risk_level: Optional risk-level filter.
        is_blocked: Optional blocked-status filter.

    Returns:
        Paginated visitor listing for administrators.
    """
    return await admin_service.get_visitors(
        limit=limit,
        offset=offset,
        risk_level=risk_level,
        is_blocked=is_blocked,
    )


@router.get("/visitors/{visitor_id}", response_model=AdminVisitorDetailResponse)
async def visitor_detail(visitor_id: str) -> AdminVisitorDetailResponse:
    """
    Return detailed admin information for a single visitor.

    Args:
        visitor_id: Identifier of the visitor to inspect.

    Returns:
        Detailed visitor view for the admin console.
    """
    return await admin_service.get_visitor_detail(visitor_id=visitor_id)


@router.get("/users", response_model=AdminListResponse)
async def users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> AdminListResponse:
    """
    Return paginated user records for administrators.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        Paginated user listing for the admin console.
    """
    return await admin_service.get_users(limit=limit, offset=offset)


@router.get("/pdfs", response_model=AdminListResponse)
async def pdfs(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    generation_type: GenerationTypeParam | None = None,
) -> AdminListResponse:
    """
    Return paginated PDF records for administrators.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        generation_type: Optional generation-type filter.

    Returns:
        Paginated PDF listing for the admin console.
    """
    return await admin_service.get_pdfs(
        limit=limit,
        offset=offset,
        generation_type=generation_type,
    )


@router.get("/fraud-events", response_model=AdminListResponse)
async def fraud_events(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    severity: RiskLevelParam | None = None,
    event_type: str | None = None,
) -> AdminListResponse:
    """
    Return paginated fraud event records for administrators.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        severity: Optional severity filter.
        event_type: Optional event-type filter.

    Returns:
        Paginated fraud event listing for the admin console.
    """
    return await admin_service.get_fraud_events(
        limit=limit,
        offset=offset,
        severity=severity,
        event_type=event_type,
    )


@router.get("/blocked-entities", response_model=AdminListResponse)
async def blocked_entities(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    entity_type: BlockedEntityTypeParam | None = None,
    is_active: bool | None = None,
) -> AdminListResponse:
    """
    Return paginated blocked entity records for administrators.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.
        entity_type: Optional blocked-entity type filter.
        is_active: Optional active-status filter.

    Returns:
        Paginated blocked-entity listing for the admin console.
    """
    return await admin_service.get_blocked_entities(
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        is_active=is_active,
    )


@router.get("/system-health", response_model=AdminSystemHealthResponse)
async def system_health() -> AdminSystemHealthResponse:
    """
    Return operational system health details for administrators.

    Returns:
        System health summary for the admin console.
    """
    return await admin_service.get_system_health()
