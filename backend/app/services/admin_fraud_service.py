from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.models.fraud_event import FraudEventType
from app.models.pdf import PDFGenerationType
from app.repositories.fraud_event_repository import FraudEventRepository
from app.repositories.pdf_repository import PDFRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.fraud_event import (
    AdminFraudSummaryResponse,
    AdminFraudVisitorItem,
    AdminFraudVisitorsResponse,
    AdminPDFItem,
    AdminPDFListResponse,
    AdminVisitorInvestigationResponse,
    FraudEventListResponse,
    TimelineItem,
)
from app.services.fraud_event_service import build_fraud_event_item
from app.services.visitor_service import build_usage_summary
from app.utils.security import utc_now


class AdminFraudService:
    def __init__(
        self,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_event_repository: FraudEventRepository | None = None,
    ) -> None:
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_event_repository = fraud_event_repository or FraudEventRepository()

    async def get_fraud_events(
        self,
        limit: int,
        severity: str | None = None,
        event_type: str | None = None,
        visitor_id: str | None = None,
        allowed: bool | None = None,
    ) -> FraudEventListResponse:
        events = await self.fraud_event_repository.list_events(
            limit=limit,
            severity=severity,
            event_type=event_type,
            visitor_id=visitor_id,
            allowed=allowed,
        )
        return FraudEventListResponse(
            total=len(events),
            limit=limit,
            items=[build_fraud_event_item(event) for event in events],
        )

    async def get_fraud_visitors(self, limit: int) -> AdminFraudVisitorsResponse:
        visitors = await self.visitor_repository.list_for_admin_fraud(limit=limit)
        return AdminFraudVisitorsResponse(
            total=len(visitors),
            limit=limit,
            items=[_build_admin_visitor_item(visitor) for visitor in visitors],
        )

    async def get_fraud_summary(self) -> AdminFraudSummaryResponse:
        return AdminFraudSummaryResponse(
            total_visitors=await self.visitor_repository.count_visitors(),
            blocked_visitors=await self.visitor_repository.count_blocked_visitors(),
            total_generated_pdfs=await self.pdf_repository.count_pdfs(),
            total_fraud_events=await self.fraud_event_repository.count_events(),
            allowed_pdf_generations=await self.fraud_event_repository.count_events(
                {
                    "event_type": FraudEventType.PDF_GENERATION_ALLOWED.value,
                    "allowed": True,
                }
            ),
            blocked_pdf_generations=await self.fraud_event_repository.count_events(
                {
                    "event_type": FraudEventType.PDF_GENERATION_BLOCKED.value,
                    "allowed": False,
                }
            ),
            high_risk_visitors=await self.visitor_repository.count_documents(
                {"risk_level": "HIGH"}
            ),
            medium_risk_visitors=await self.visitor_repository.count_documents(
                {"risk_level": "MEDIUM"}
            ),
            low_risk_visitors=await self.visitor_repository.count_documents(
                {"risk_level": "LOW"}
            ),
        )

    async def get_visitor_investigation(
        self,
        visitor_id: str,
    ) -> AdminVisitorInvestigationResponse:
        visitor = await self.visitor_repository.get_by_id(visitor_id)
        if visitor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visitor not found.",
            )

        pdfs = await self.pdf_repository.list_by_visitor_id(visitor_id, limit=100)
        fraud_events = await self.fraud_event_repository.list_by_visitor_id(
            visitor_id,
            limit=100,
        )
        pdf_items = [_build_admin_pdf_item(pdf) for pdf in pdfs]
        event_items = [build_fraud_event_item(event) for event in fraud_events]
        timeline = _build_timeline(visitor, pdfs, fraud_events)
        return AdminVisitorInvestigationResponse(
            visitor=_sanitize_visitor(visitor),
            generated_pdfs=pdf_items,
            fraud_events=event_items,
            timeline=timeline,
        )

    async def get_all_pdfs(self, limit: int) -> AdminPDFListResponse:
        pdfs = await self.pdf_repository.list_all(limit=limit)
        return AdminPDFListResponse(
            total=len(pdfs),
            limit=limit,
            items=[_build_admin_pdf_item(pdf) for pdf in pdfs],
        )


def _build_admin_visitor_item(visitor: dict[str, Any]) -> AdminFraudVisitorItem:
    usage_summary = build_usage_summary(visitor)
    return AdminFraudVisitorItem(
        visitor_id=str(visitor.get("_id", "")),
        **usage_summary,
        risk_score=int(visitor.get("risk_score", 0)),
        risk_level=str(visitor.get("risk_level", "LOW")),
        is_blocked=bool(visitor.get("is_blocked", False)),
        block_reason=visitor.get("block_reason"),
        local_storage_id_count=len(visitor.get("local_storage_ids", [])),
        session_id_count=len(visitor.get("session_ids", [])),
        fingerprint_hash_count=len(visitor.get("fingerprint_hashes", [])),
        ip_address_count=len(visitor.get("ip_addresses", [])),
        user_agent_count=len(visitor.get("user_agents", [])),
        first_seen_at=_datetime_or_now(visitor.get("created_at")),
        last_seen_at=_datetime_or_now(visitor.get("last_seen_at")),
    )


def _build_admin_pdf_item(pdf: dict[str, Any]) -> AdminPDFItem:
    return AdminPDFItem(
        pdf_id=str(pdf.get("_id", "")),
        visitor_id=pdf.get("visitor_id"),
        title=str(pdf.get("title", "")),
        file_name=str(pdf.get("file_name", "")),
        file_path=str(pdf.get("file_path", "")),
        generation_type=str(
            pdf.get("generation_type", PDFGenerationType.ANONYMOUS.value)
        ),
        fingerprint_hash=pdf.get("fingerprint_hash"),
        ip_address=pdf.get("ip_address"),
        created_at=_datetime_or_now(pdf.get("created_at")),
    )


def _sanitize_visitor(visitor: dict[str, Any]) -> dict[str, Any]:
    return {
        "visitor_id": str(visitor.get("_id", "")),
        "cookie_id": visitor.get("cookie_id"),
        "local_storage_ids": visitor.get("local_storage_ids", []),
        "session_ids": visitor.get("session_ids", []),
        "fingerprint_hashes": visitor.get("fingerprint_hashes", []),
        "primary_fingerprint_hash": visitor.get("primary_fingerprint_hash"),
        "ip_addresses": visitor.get("ip_addresses", []),
        "user_agents": visitor.get("user_agents", []),
        "device_info": visitor.get("device_info", {}),
        "free_usage_count": int(visitor.get("free_usage_count", 0)),
        "risk_score": int(visitor.get("risk_score", 0)),
        "risk_level": str(visitor.get("risk_level", "LOW")),
        "is_blocked": bool(visitor.get("is_blocked", False)),
        "block_reason": visitor.get("block_reason"),
        "created_at": _datetime_or_now(visitor.get("created_at")),
        "last_seen_at": _datetime_or_now(visitor.get("last_seen_at")),
    }


def _build_timeline(
    visitor: dict[str, Any],
    pdfs: list[dict[str, Any]],
    fraud_events: list[dict[str, Any]],
) -> list[TimelineItem]:
    timeline = [
        TimelineItem(
            id=str(visitor.get("_id", "")),
            item_type="VISITOR",
            title="Visitor first seen",
            metadata={"risk_level": visitor.get("risk_level", "LOW")},
            created_at=_datetime_or_now(visitor.get("created_at")),
        )
    ]
    timeline.extend(
        TimelineItem(
            id=str(pdf.get("_id", "")),
            item_type="PDF",
            title=str(pdf.get("title", "PDF generated")),
            metadata={
                "file_name": pdf.get("file_name", ""),
                "generation_type": pdf.get("generation_type", ""),
            },
            created_at=_datetime_or_now(pdf.get("created_at")),
        )
        for pdf in pdfs
    )
    timeline.extend(
        TimelineItem(
            id=str(event.get("id") or event.get("_id") or ""),
            item_type="FRAUD_EVENT",
            title=str(event.get("event_type", "")),
            metadata={
                "severity": event.get("severity", ""),
                "allowed": bool(event.get("allowed", True)),
                "reason": event.get("reason"),
            },
            created_at=_datetime_or_now(event.get("created_at")),
        )
        for event in fraud_events
    )
    return sorted(timeline, key=lambda item: item.created_at, reverse=True)


def _datetime_or_now(value: Any) -> datetime:
    return value if isinstance(value, datetime) else utc_now()
