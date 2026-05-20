import asyncio
from typing import Any

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.core.auth import get_current_user_optional
from app.core.public_config import LOGIN_REQUIRED_MESSAGE, get_visitor_cookie
from app.models.fraud import BlockedEntityType, FraudEventType, FraudSeverity
from app.models.fraud_event import (
    FraudEventType as AdminFraudEventType,
    FraudSeverity as AdminFraudSeverity,
)
from app.models.user import UserRole
from app.models.pdf import PDFGenerationType
from app.models.pdf import PDFOwnerType
from app.repositories.pdf_repository import PDFRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.pdf import (
    MyPDFHistoryItem,
    MyPDFHistoryResponse,
    PDFGenerateRequest,
    PDFGenerateResponse,
    PDFHistoryItem,
    PDFHistoryResponse,
)
from app.services.fraud_event_service import FraudEventService
from app.services.fraud_service import FraudService
from app.services.user_usage_service import UserUsageService
from app.services.visitor_service import build_usage_summary
from app.utils.pdf_generator import generate_simple_pdf
from app.utils.security import generate_uuid, normalize_ip, utc_now

class PDFService:
    def __init__(
        self,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_service: FraudService | None = None,
        fraud_event_service: FraudEventService | None = None,
        user_usage_service: UserUsageService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_service = fraud_service or FraudService()
        self.fraud_event_service = fraud_event_service or FraudEventService()
        self.user_usage_service = user_usage_service or UserUsageService()

    async def generate_pdf_for_anonymous_visitor(
        self,
        request: Request,
        payload: PDFGenerateRequest,
    ) -> PDFGenerateResponse:
        return await self.generate_pdf(request=request, payload=payload)

    async def generate_pdf(
        self,
        request: Request,
        payload: PDFGenerateRequest,
    ) -> PDFGenerateResponse:
        current_user = await get_current_user_optional(request)
        visitor = await self._get_optional_visitor_from_request(request)

        if current_user is not None:
            return await self._generate_pdf_for_authenticated_user(
                request=request,
                payload=payload,
                current_user=current_user,
                visitor=visitor,
            )

        return await self._generate_pdf_for_anonymous_visitor(
            request=request,
            payload=payload,
        )

    async def _generate_pdf_for_anonymous_visitor(
        self,
        request: Request,
        payload: PDFGenerateRequest,
    ) -> PDFGenerateResponse:
        visitor = await self._get_visitor_from_request(request)

        if bool(visitor.get("is_blocked", False)):
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=visitor,
                event_type=AdminFraudEventType.PDF_GENERATION_BLOCKED.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="PDF generation blocked.",
                allowed=False,
                reason=visitor.get("block_reason") or "VISITOR_BLOCKED",
                metadata={"title": payload.title},
            )
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
                detail=_build_limit_response(
                    free_limit=self.settings.FREE_USAGE_LIMIT,
                    used=min(
                        int(visitor.get("free_usage_count", 0)),
                        self.settings.FREE_USAGE_LIMIT,
                    ),
                ),
            )

        free_usage_count = int(visitor.get("free_usage_count", 0))
        if free_usage_count >= self.settings.FREE_USAGE_LIMIT:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=visitor,
                event_type=AdminFraudEventType.PDF_GENERATION_BLOCKED.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="PDF generation blocked.",
                allowed=False,
                reason="FREE_LIMIT_REACHED",
                metadata={"title": payload.title},
            )
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=visitor,
                event_type=AdminFraudEventType.FREE_LIMIT_REACHED.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="Anonymous free usage limit reached.",
                allowed=False,
                reason="FREE_LIMIT_REACHED",
                metadata={
                    "free_usage_count": free_usage_count,
                    "free_usage_limit": self.settings.FREE_USAGE_LIMIT,
                },
            )
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
            blocked_visitor = await self.visitor_repository.get_by_id(visitor["_id"])
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=blocked_visitor or visitor,
                event_type=AdminFraudEventType.VISITOR_BLOCKED.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="Visitor blocked.",
                allowed=False,
                reason="FREE_LIMIT_REACHED",
                metadata={
                    "free_usage_count": free_usage_count,
                    "free_usage_limit": self.settings.FREE_USAGE_LIMIT,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_build_limit_response(
                    free_limit=self.settings.FREE_USAGE_LIMIT,
                    used=free_usage_count,
                ),
            )

        try:
            file_name, file_path = await asyncio.to_thread(
                generate_simple_pdf,
                title=payload.title,
                content=payload.content,
                output_dir=self.settings.PDF_STORAGE_DIR,
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
                "owner_type": PDFOwnerType.ANONYMOUS.value,
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
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=updated_visitor,
                event_type=AdminFraudEventType.PDF_GENERATION_ALLOWED.value,
                severity=AdminFraudSeverity.LOW.value,
                action="PDF generation allowed.",
                allowed=True,
                metadata={"pdf_id": pdf_id, "title": payload.title},
            )
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
            title=payload.title,
            file_name=file_name,
            free_limit=usage_summary["free_usage_limit"],
            used=usage_summary["free_usage_count"],
            remaining=usage_summary["remaining_free_uses"],
        )

    async def get_pdf_history_for_visitor(self, request: Request) -> PDFHistoryResponse:
        return await self.get_pdf_history(request=request)

    async def get_my_pdf_history(self, request: Request) -> MyPDFHistoryResponse:
        current_user = await get_current_user_optional(request)
        if current_user is not None:
            pdf_records = await self.pdf_repository.list_by_user_id(current_user["_id"])
            items = [_build_my_history_item(pdf_record) for pdf_record in pdf_records]
            return MyPDFHistoryResponse(total=len(items), items=items)

        visitor = await self._get_visitor_from_request(request)
        pdf_records = await self.pdf_repository.list_by_visitor_id(visitor["_id"])
        items = [_build_my_history_item(pdf_record) for pdf_record in pdf_records]
        return MyPDFHistoryResponse(
            total=len(items),
            items=items,
        )

    async def get_pdf_history(self, request: Request) -> PDFHistoryResponse:
        current_user = await get_current_user_optional(request)
        if current_user is not None:
            visitor = await self._get_optional_visitor_from_request(request)
            linked_visitor_ids = list(current_user.get("linked_visitor_ids", []))
            if visitor is not None and visitor["_id"] not in linked_visitor_ids:
                linked_visitor_ids.append(visitor["_id"])
            pdf_records = await self.pdf_repository.list_by_user_or_linked_visitors(
                user_id=current_user["_id"],
                visitor_ids=linked_visitor_ids,
            )
            items = [_build_history_item(pdf_record) for pdf_record in pdf_records]
            visitor_id = (
                visitor["_id"]
                if visitor is not None
                else _first_or_empty(linked_visitor_ids)
            )
            return PDFHistoryResponse(
                visitor_id=visitor_id,
                total=len(items),
                items=items,
            )

        visitor = await self._get_visitor_from_request(request)
        pdf_records = await self.pdf_repository.list_by_visitor_id(visitor["_id"])
        items = [_build_history_item(pdf_record) for pdf_record in pdf_records]
        return PDFHistoryResponse(
            visitor_id=visitor["_id"],
            total=len(items),
            items=items,
        )

    async def _generate_pdf_for_authenticated_user(
        self,
        request: Request,
        payload: PDFGenerateRequest,
        current_user: dict[str, Any],
        visitor: dict[str, Any] | None,
    ) -> PDFGenerateResponse:
        usage = await self.user_usage_service.get_current_usage(current_user)
        if usage["used"] >= usage["limit"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": "Monthly PDF limit reached. Please upgrade your plan to continue.",
                    "requires_upgrade": True,
                    "plan": usage["plan"],
                    "used": usage["used"],
                    "limit": usage["limit"],
                    "remaining": 0,
                },
            )

        try:
            file_name, file_path = await asyncio.to_thread(
                generate_simple_pdf,
                title=payload.title,
                content=payload.content,
                output_dir=self.settings.PDF_STORAGE_DIR,
            )
            pdf_id = generate_uuid()
            pdf_data = {
                "_id": pdf_id,
                "visitor_id": visitor["_id"] if visitor is not None else None,
                "user_id": current_user["_id"],
                "title": payload.title,
                "content": payload.content,
                "file_name": file_name,
                "file_path": file_path,
                "generation_type": PDFGenerationType.AUTHENTICATED.value,
                "owner_type": PDFOwnerType.USER.value,
                "created_at": utc_now(),
                "ip_address": normalize_ip(request.client.host if request.client else ""),
                "fingerprint_hash": (
                    visitor.get("primary_fingerprint_hash")
                    if visitor is not None
                    else None
                ),
            }
            await self.pdf_repository.create_pdf_record(pdf_data)
            usage = await self.user_usage_service.increment_after_generation(current_user)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to generate PDF. Please try again.",
            ) from exc

        return PDFGenerateResponse(
            success=True,
            message="PDF generated successfully.",
            pdf_id=pdf_id,
            title=payload.title,
            file_name=file_name,
            plan=usage["plan"],
            limit=usage["limit"],
            used=usage["used"],
            remaining=usage["remaining"],
        )

    async def get_downloadable_pdf(
        self,
        request: Request,
        pdf_id: str,
        allow_admin: bool = False,
    ) -> dict[str, Any]:
        pdf_record = await self.pdf_repository.get_by_id(pdf_id)
        if pdf_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found.")

        current_user = await get_current_user_optional(request)
        if allow_admin:
            return pdf_record
        if current_user is not None and current_user.get("role") == UserRole.ADMIN.value:
            return pdf_record
        if current_user is not None and pdf_record.get("user_id") == current_user["_id"]:
            return pdf_record

        visitor = await self._get_optional_visitor_from_request(request)
        if (
            current_user is None
            and visitor is not None
            and pdf_record.get("visitor_id") == visitor["_id"]
            and not pdf_record.get("user_id")
        ):
            return pdf_record

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="PDF not found.")

    async def _get_visitor_from_request(self, request: Request) -> dict[str, Any]:
        cookie_id = get_visitor_cookie(request.cookies)
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

    async def _get_optional_visitor_from_request(
        self,
        request: Request,
    ) -> dict[str, Any] | None:
        cookie_id = get_visitor_cookie(request.cookies)
        if not cookie_id:
            return None
        return await self.visitor_repository.find_by_cookie_id(cookie_id)

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
                        "cookie_id": get_visitor_cookie(request.cookies),
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


def _build_my_history_item(pdf_record: dict[str, Any]) -> MyPDFHistoryItem:
    return MyPDFHistoryItem(
        pdf_id=pdf_record["_id"],
        title=pdf_record.get("title", ""),
        file_name=pdf_record.get("file_name", ""),
        created_at=pdf_record["created_at"],
        download_url=f"/api/pdf/download/{pdf_record['_id']}",
    )


def _last_or_none(values: list[Any]) -> Any:
    return values[-1] if values else None


def _first_or_empty(values: list[str]) -> str:
    return values[0] if values else ""


def _build_limit_response(free_limit: int, used: int) -> dict[str, int | bool | str]:
    return {
        "success": False,
        "message": LOGIN_REQUIRED_MESSAGE,
        "free_limit": free_limit,
        "used": min(used, free_limit),
        "remaining": 0,
        "requires_login": True,
    }
