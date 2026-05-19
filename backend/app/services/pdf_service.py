import asyncio
from typing import Any

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.models.fraud import BlockedEntityType, FraudEventType, FraudSeverity
from app.models.pdf import PDFGenerationType
from app.repositories.pdf_repository import PDFRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.pdf import (
    PDFGenerateRequest,
    PDFGenerateResponse,
    PDFHistoryItem,
    PDFHistoryResponse,
)
from app.services.fraud_service import FraudService
from app.services.visitor_service import build_usage_summary
from app.utils.pdf_generator import generate_simple_pdf
from app.utils.security import generate_uuid, normalize_ip, utc_now

ANON_COOKIE_NAME = "anon_id"


class PDFService:
    def __init__(
        self,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_service: FraudService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_service = fraud_service or FraudService()

    async def generate_pdf_for_anonymous_visitor(
        self,
        request: Request,
        payload: PDFGenerateRequest,
    ) -> PDFGenerateResponse:
        visitor = await self._get_visitor_from_request(request)

        if bool(visitor.get("is_blocked", False)):
            await self._create_pdf_fraud_event(
                visitor=visitor,
                request=request,
                event_type=FraudEventType.BLOCKED_VISITOR_REQUEST.value,
                severity=FraudSeverity.HIGH.value,
                risk_points=10,
                message="Blocked visitor attempted to generate PDF.",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Visitor is blocked. Please login to continue.",
            )

        free_usage_count = int(visitor.get("free_usage_count", 0))
        if free_usage_count >= self.settings.FREE_USAGE_LIMIT:
            await self._create_pdf_fraud_event(
                visitor=visitor,
                request=request,
                event_type=FraudEventType.FREE_LIMIT_REACHED.value,
                severity=FraudSeverity.HIGH.value,
                risk_points=40,
                message="Anonymous free usage limit reached.",
            )
            await self.visitor_repository.mark_visitor_blocked(
                visitor_id=visitor["_id"],
                reason="FREE_LIMIT_REACHED",
            )
            await self.fraud_service.create_blocked_entity(
                entity_type=BlockedEntityType.VISITOR.value,
                entity_value=visitor["_id"],
                reason="FREE_LIMIT_REACHED",
                risk_score=int(visitor.get("risk_score", 0)),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": "Free limit reached. Please login to continue.",
                    "reason": "FREE_LIMIT_REACHED",
                    "free_usage_count": free_usage_count,
                    "free_usage_limit": self.settings.FREE_USAGE_LIMIT,
                    "remaining_free_uses": 0,
                },
            )

        try:
            file_name, file_path = await asyncio.to_thread(
                generate_simple_pdf,
                title=payload.title,
                content=payload.content,
            )
            pdf_id = generate_uuid()
            pdf_data = {
                "_id": pdf_id,
                "visitor_id": visitor["_id"],
                "user_id": None,
                "title": payload.title,
                "content": payload.content,
                "file_name": file_name,
                "file_path": file_path,
                "generation_type": PDFGenerationType.ANONYMOUS.value,
                "created_at": utc_now(),
                "ip_address": normalize_ip(request.client.host if request.client else ""),
                "fingerprint_hash": visitor.get("primary_fingerprint_hash", ""),
            }
            await self.pdf_repository.create_pdf_record(pdf_data)
            updated_visitor = await self.visitor_repository.increment_free_usage(
                visitor_id=visitor["_id"]
            )
            if updated_visitor is None:
                raise RuntimeError("Visitor usage update failed")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to generate PDF. Please try again.",
            ) from exc

        usage_summary = build_usage_summary(updated_visitor or visitor)
        return PDFGenerateResponse(
            success=True,
            message="PDF generated successfully.",
            pdf_id=pdf_id,
            file_name=file_name,
            file_path=file_path,
            **usage_summary,
        )

    async def get_pdf_history_for_visitor(self, request: Request) -> PDFHistoryResponse:
        visitor = await self._get_visitor_from_request(request)
        pdf_records = await self.pdf_repository.list_by_visitor_id(visitor["_id"])
        items = [_build_history_item(pdf_record) for pdf_record in pdf_records]
        return PDFHistoryResponse(
            visitor_id=visitor["_id"],
            total=len(items),
            items=items,
        )

    async def _get_visitor_from_request(self, request: Request) -> dict[str, Any]:
        cookie_id = request.cookies.get(ANON_COOKIE_NAME)
        if not cookie_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Visitor cookie not found. Please call /api/visitor/identify first.",
            )

        visitor = await self.visitor_repository.find_by_cookie_id(cookie_id)
        if visitor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visitor not found. Please identify visitor again.",
            )
        return visitor

    async def _create_pdf_fraud_event(
        self,
        visitor: dict[str, Any],
        request: Request,
        event_type: str,
        severity: str,
        risk_points: int,
        message: str,
    ) -> None:
        await self.fraud_service.create_fraud_events(
            visitor_id=visitor["_id"],
            events=[
                {
                    "event_type": event_type,
                    "severity": severity,
                    "risk_points": risk_points,
                    "message": message,
                    "signals": {
                        "cookie_id": request.cookies.get(ANON_COOKIE_NAME),
                        "local_storage_id": _last_or_none(
                            visitor.get("local_storage_ids", [])
                        ),
                        "session_id": _last_or_none(visitor.get("session_ids", [])),
                        "fingerprint_hash": visitor.get("primary_fingerprint_hash"),
                        "ip_address": normalize_ip(
                            request.client.host if request.client else ""
                        ),
                        "user_agent": request.headers.get("user-agent"),
                    },
                }
            ],
        )


def _build_history_item(pdf_record: dict[str, Any]) -> PDFHistoryItem:
    return PDFHistoryItem(
        pdf_id=pdf_record["_id"],
        title=pdf_record.get("title", ""),
        file_name=pdf_record.get("file_name", ""),
        generation_type=pdf_record.get("generation_type", PDFGenerationType.ANONYMOUS.value),
        created_at=pdf_record["created_at"],
    )


def _last_or_none(values: list[Any]) -> Any:
    return values[-1] if values else None
