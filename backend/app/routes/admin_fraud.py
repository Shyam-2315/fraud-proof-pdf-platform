from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.admin_auth import require_admin_api_key
from app.config import get_settings
from app.models.fraud_event import AdminAuditAction
from app.schemas.fraud_event import (
    AdminAuditLogItem,
    AdminAuditLogListResponse,
    AdminFraudSummaryResponse,
    AdminFraudVisitorsResponse,
    AdminPDFListResponse,
    AdminVisitorInvestigationResponse,
    FraudEventListResponse,
    FraudLabelRequest,
    MLTrainRequest,
)
from app.services.admin_audit_service import AdminAuditService
from app.services.admin_fraud_service import AdminFraudService
from app.fraud_engine.model_registry import ModelRegistry
from app.fraud_engine.training_service import TrainingService
from app.models.fraud_event import FraudEventType, FraudSeverity
from app.repositories.fraud_engine_repository import FraudEngineRepository
from app.services.fraud_event_service import FraudEventService
from app.services.rate_limit_service import RateLimitService, client_ip
from app.utils.security import generate_uuid, utc_now

router = APIRouter(
    prefix="/api/admin",
    dependencies=[Depends(require_admin_api_key)],
)
admin_fraud_service = AdminFraudService()
admin_audit_service = AdminAuditService()
fraud_engine_repository = FraudEngineRepository()
model_registry = ModelRegistry(repository=fraud_engine_repository)
training_service = TrainingService(repository=fraud_engine_repository, registry=model_registry)
fraud_event_service = FraudEventService()
settings = get_settings()
rate_limit_service = RateLimitService()

SeverityParam = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@router.get(
    "/fraud/events",
    response_model=FraudEventListResponse,
    tags=["Admin Fraud"],
)
async def admin_fraud_events(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    severity: SeverityParam | None = None,
    event_type: str | None = None,
    visitor_id: str | None = None,
    allowed: bool | None = None,
) -> FraudEventListResponse:
    await _enforce_admin_rate_limit(request)
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
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminFraudVisitorsResponse:
    await _enforce_admin_rate_limit(request)
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
async def admin_fraud_summary(request: Request) -> AdminFraudSummaryResponse:
    await _enforce_admin_rate_limit(request)
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
    request: Request,
    visitor_id: str,
) -> AdminVisitorInvestigationResponse:
    await _enforce_admin_rate_limit(request)
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
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminPDFListResponse:
    await _enforce_admin_rate_limit(request)
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
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> AdminAuditLogListResponse:
    await _enforce_admin_rate_limit(request)
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


@router.post("/fraud/label", tags=["Admin Fraud"])
async def admin_apply_fraud_label(
    request: Request,
    payload: FraudLabelRequest,
) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    if payload.label not in {0, 1}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="label must be 0 or 1")
    label_id = generate_uuid()
    label = await fraud_engine_repository.create_label(
        {
            "_id": label_id,
            "id": label_id,
            "visitor_id": payload.visitor_id,
            "label": payload.label,
            "source": "ADMIN_REVIEW",
            "notes": payload.notes,
            "created_by_admin": None,
            "created_at": utc_now(),
        }
    )
    updated_events = await fraud_engine_repository.update_training_labels_for_visitor(
        visitor_id=payload.visitor_id,
        label=payload.label,
        source="ADMIN_REVIEW",
        confidence=1.0,
    )
    await fraud_event_service.create_event(
        visitor_id=payload.visitor_id,
        event_type=FraudEventType.ADMIN_LABEL_APPLIED.value,
        severity=FraudSeverity.MEDIUM.value,
        action="Admin label applied.",
        allowed=True,
        reason=payload.notes,
        metadata={"label": payload.label, "updated_training_events": updated_events},
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_APPLIED_FRAUD_LABEL.value,
        target_type="visitor",
        target_id=payload.visitor_id,
        metadata={"label": payload.label, "notes": payload.notes},
    )
    return {"success": True, "label": label, "updated_training_events": updated_events}


@router.get("/fraud/decisions", tags=["Admin Fraud"])
async def admin_fraud_decisions(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    visitor_id: str | None = None,
    action_type: str | None = None,
) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    decisions = await fraud_engine_repository.list_decisions(
        limit=limit,
        visitor_id=visitor_id,
        action_type=action_type,
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_FRAUD_EVENTS.value,
        target_type="fraud_decisions",
        metadata={
            "limit": limit,
            "visitor_id": visitor_id,
            "action_type": action_type,
        },
    )
    return {"total": len(decisions), "limit": limit, "items": _sanitize_doc(decisions)}


@router.get("/fraud/features/{visitor_id}", tags=["Admin Fraud"])
async def admin_fraud_features(
    request: Request,
    visitor_id: str,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    snapshots = await fraud_engine_repository.list_feature_snapshots_by_visitor(
        visitor_id=visitor_id,
        limit=limit,
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_VISITOR_INVESTIGATION.value,
        target_type="fraud_feature_snapshots",
        target_id=visitor_id,
        metadata={"limit": limit},
    )
    return {"total": len(snapshots), "limit": limit, "items": _sanitize_doc(snapshots)}


@router.get("/fraud/identity-links/{visitor_id}", tags=["Admin Fraud"])
async def admin_fraud_identity_links(
    request: Request,
    visitor_id: str,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    links = await admin_fraud_service.identity_link_repository.list_by_visitor_id(
        visitor_id=visitor_id,
        limit=limit,
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_VISITOR_INVESTIGATION.value,
        target_type="visitor_identity_links",
        target_id=visitor_id,
        metadata={"limit": limit},
    )
    return {"total": len(links), "limit": limit, "items": _sanitize_doc(links)}


@router.get("/fraud/ip-usage", tags=["Admin Fraud"])
async def admin_ip_usage(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    return await admin_fraud_service.get_ip_usage_list(limit=limit)


@router.get("/fraud/ip-usage/{ip_address}", tags=["Admin Fraud"])
async def admin_ip_usage_detail(
    request: Request,
    ip_address: str,
) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    return await admin_fraud_service.get_ip_usage_detail(ip_address=ip_address)


@router.get("/ml/models", tags=["Admin ML"])
async def admin_ml_models(request: Request) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    versions = await model_registry.list_versions()
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_ML_MODELS.value,
        target_type="ml_model_versions",
    )
    return {"total": len(versions), "items": [_sanitize_doc(item) for item in versions]}


@router.get("/ml/models/active", tags=["Admin ML"])
async def admin_active_ml_model(request: Request) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    active = model_registry.active_config()
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_VIEWED_ML_MODELS.value,
        target_type="active_ml_model",
    )
    return {"success": True, "active_model": active}


@router.post("/ml/train", tags=["Admin ML"])
async def admin_train_ml_model(request: Request, payload: MLTrainRequest) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    if not settings.ENABLE_ONLINE_ML_TRAINING:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Online ML training is disabled in this environment. "
                "Run training locally and upload model files, or enable it in environment settings."
            ),
        )
    result = await training_service.train(
        synthetic_csv=payload.synthetic_csv,
        demo=payload.demo,
        auto_activate=payload.auto_activate,
        min_confidence=payload.min_confidence,
        model_type=payload.model_type,
    )
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_TRAINED_ML_MODEL.value,
        target_type="ml_training",
        metadata={"result_success": result.get("success"), "auto_activate": payload.auto_activate},
    )
    return _sanitize_doc(result)


@router.post("/ml/models/{model_version_id}/activate", tags=["Admin ML"])
async def admin_activate_ml_model(request: Request, model_version_id: str) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    model = await model_registry.activate(model_version_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_ACTIVATED_ML_MODEL.value,
        target_type="ml_model_version",
        target_id=model_version_id,
    )
    return {"success": True, "model": _sanitize_doc(model)}


@router.post("/ml/models/{model_version_id}/reject", tags=["Admin ML"])
async def admin_reject_ml_model(request: Request, model_version_id: str) -> dict[str, object]:
    await _enforce_admin_rate_limit(request)
    model = await model_registry.reject(model_version_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    await admin_audit_service.log_access(
        action=AdminAuditAction.ADMIN_REJECTED_ML_MODEL.value,
        target_type="ml_model_version",
        target_id=model_version_id,
    )
    return {"success": True, "model": _sanitize_doc(model)}


def _sanitize_doc(value):
    if isinstance(value, list):
        return [_sanitize_doc(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_doc(item) for key, item in value.items() if key != "_id"}
    return value


async def _enforce_admin_rate_limit(request: Request) -> None:
    await rate_limit_service.check(
        request,
        bucket="admin",
        identifier=client_ip(request),
        rate=settings.ADMIN_RATE_LIMIT,
    )
