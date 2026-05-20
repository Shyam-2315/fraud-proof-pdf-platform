from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.admin_auth import require_admin_api_key
from app.models.fraud_event import AdminAuditAction
from app.schemas.fraud_event import (
    AdminAuditLogItem,
    AdminAuditLogListResponse,
    AdminFraudSummaryResponse,
    AdminFraudVisitorsResponse,
    AdminPDFListResponse,
    AdminVisitorInvestigationResponse,
    FraudEventListResponse,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.admin_fraud_service import AdminFraudService

router = APIRouter(
    prefix="/api/admin",
    dependencies=[Depends(require_admin_api_key)],
)
admin_fraud_service = AdminFraudService()
admin_audit_service = AdminAuditService()

SeverityParam = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@router.get(
    "/fraud/events",
    response_model=FraudEventListResponse,
    tags=["Admin Fraud"],
)
async def admin_fraud_events(
    limit: int = Query(default=50, ge=1, le=500),
    severity: SeverityParam | None = None,
    event_type: str | None = None,
    visitor_id: str | None = None,
    allowed: bool | None = None,
) -> FraudEventListResponse:
    response = await admin_fraud_service.get_fraud_events(
        limit=limit,
        severity=severity,
        event_type=event_type,
        visitor_id=visitor_id,
        allowed=allowed,
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_FRAUD_EVENTS.value,
        target_type="fraud_events",
        metadata={
            "limit": limit,
            "severity": severity,
            "event_type": event_type,
            "visitor_id": visitor_id,
            "allowed": allowed,
        },
    )
    return response


@router.get(
    "/fraud/visitors",
    response_model=AdminFraudVisitorsResponse,
    tags=["Admin Fraud"],
)
async def admin_fraud_visitors(
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminFraudVisitorsResponse:
    response = await admin_fraud_service.get_fraud_visitors(limit=limit)
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_FRAUD_VISITORS.value,
        target_type="visitors",
        metadata={"limit": limit},
    )
    return response


@router.get(
    "/fraud/summary",
    response_model=AdminFraudSummaryResponse,
    tags=["Admin Fraud"],
)
async def admin_fraud_summary() -> AdminFraudSummaryResponse:
    response = await admin_fraud_service.get_fraud_summary()
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_FRAUD_SUMMARY.value,
        target_type="fraud_summary",
    )
    return response


@router.get(
    "/fraud/visitor/{visitor_id}",
    response_model=AdminVisitorInvestigationResponse,
    tags=["Admin Fraud"],
)
async def admin_visitor_investigation(
    visitor_id: str,
) -> AdminVisitorInvestigationResponse:
    response = await admin_fraud_service.get_visitor_investigation(
        visitor_id=visitor_id,
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_VISITOR_INVESTIGATION.value,
        target_type="visitor",
        target_id=visitor_id,
    )
    return response


@router.get("/pdfs", response_model=AdminPDFListResponse, tags=["Admin PDFs"])
async def admin_pdfs(
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminPDFListResponse:
    response = await admin_fraud_service.get_all_pdfs(limit=limit)
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_ALL_PDFS.value,
        target_type="generated_pdfs",
        metadata={"limit": limit},
    )
    return response


@router.get(
    "/audit-logs",
    response_model=AdminAuditLogListResponse,
    tags=["Admin Audit"],
)
async def admin_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminAuditLogListResponse:
    logs = await admin_audit_service.list_logs(limit=limit)
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_AUDIT_LOGS.value,
        target_type="admin_audit_logs",
        metadata={"limit": limit},
    )
    return AdminAuditLogListResponse(
        total=len(logs),
        limit=limit,
        items=[
            AdminAuditLogItem(
                id=str(log.get("id") or log.get("_id") or ""),
                action=str(log.get("action", "")),
                target_type=str(log.get("target_type", "")),
                target_id=log.get("target_id"),
                metadata=dict(log.get("metadata", {})),
                created_at=log["created_at"],
            )
            for log in logs
        ],
    )
