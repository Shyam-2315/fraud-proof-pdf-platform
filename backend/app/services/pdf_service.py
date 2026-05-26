import asyncio
import logging
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.core.auth import get_current_user_optional
from app.core.public_config import get_visitor_cookie
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
from app.services.anonymous_usage_service import AnonymousUsageService
from app.services.behavior_service import BehaviorService, content_hash
from app.services.fraud_decision_service import FraudDecisionService
from app.services.fraud_service import FraudService
from app.services.ip_intelligence import IPIntelligence
from app.services.risk_engine import RiskEngine
from app.services.rate_limit_service import client_ip
from app.services.user_usage_service import UserUsageService
from app.services.visitor_service import VisitorService
from app.utils.request_utils import get_client_ip_details, get_normalized_client_ip
from app.utils.pdf_generator import generate_simple_pdf
from app.utils.security import generate_uuid, normalize_ip, utc_now

logger = logging.getLogger(__name__)


class PDFService:
    def __init__(
        self,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_service: FraudService | None = None,
        fraud_event_service: FraudEventService | None = None,
        user_usage_service: UserUsageService | None = None,
        fraud_decision_service: FraudDecisionService | None = None,
        behavior_service: BehaviorService | None = None,
        visitor_service: VisitorService | None = None,
        anonymous_usage_service: AnonymousUsageService | None = None,
        ip_intelligence: IPIntelligence | None = None,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self.settings = get_settings()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_service = fraud_service or FraudService()
        self.fraud_event_service = fraud_event_service or FraudEventService()
        self.user_usage_service = user_usage_service or UserUsageService()
        self.fraud_decision_service = fraud_decision_service or FraudDecisionService()
        self.behavior_service = behavior_service or BehaviorService()
        self.visitor_service = visitor_service or VisitorService(repository=self.visitor_repository)
        self.anonymous_usage_service = anonymous_usage_service or AnonymousUsageService()
        self.ip_intelligence = ip_intelligence or IPIntelligence()
        self.risk_engine = risk_engine or RiskEngine()

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
        if current_user is not None:
            visitor = await self._get_optional_visitor_from_request(request)
            return await self._generate_pdf_for_authenticated_user(
                request=request,
                payload=payload,
                current_user=current_user,
                visitor=visitor,
            )

        visitor = await self._get_visitor_from_request(request)
        return await self._generate_pdf_for_anonymous_visitor(
            request=request,
            payload=payload,
            visitor=visitor,
        )

    async def _generate_pdf_for_anonymous_visitor(
        self,
        request: Request,
        payload: PDFGenerateRequest,
        visitor: dict[str, Any],
    ) -> PDFGenerateResponse:
        ip_details = get_client_ip_details(request)
        ip_address = get_normalized_client_ip(request)
        anon_id = request.headers.get("X-Anon-Id") or get_visitor_cookie(request.cookies)
        fingerprint_hash = request.headers.get("X-Device-Fingerprint")
        user_agent = request.headers.get("user-agent")
        shared_usage_snapshot = await self.anonymous_usage_service.get_shared_usage_snapshot(
            visitor=visitor,
            ip_address=ip_address,
        )
        shared_used = int(shared_usage_snapshot["free_usage_count"])
        shared_limit = int(shared_usage_snapshot["free_usage_limit"])
        if shared_used >= shared_limit:
            await self.behavior_service.record_internal_event(
                visitor_id=visitor["_id"],
                user_id=None,
                event_type="LIMIT_REACHED",
                metadata={"reason": "SHARED_IP_FREE_LIMIT_REACHED"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_build_limit_response(message="Free limit reached. Please log in to continue."),
            )

        active_window = shared_usage_snapshot.get("active_window")
        ip_intelligence = await self.ip_intelligence.lookup(ip_address)
        behavior_summary = await self._behavior_summary(visitor["_id"])
        risk_decision = self.risk_engine.decide(
            {
                "visitor_usage_count": int(shared_usage_snapshot["visitor_usage_count"]),
                "shared_ip_usage_count": int((active_window or {}).get("anonymous_pdf_count", 0)),
                "shared_usage_count": shared_used,
                "anon_shared_limit": shared_limit,
                "unique_visitors_from_ip": len((active_window or {}).get("visitor_ids", [])),
                "ip_change_count": max(len(visitor.get("ip_addresses", [])) - 1, 0),
                "proxy_chain_hop_count": int(ip_details.get("proxy_hop_count", 0)),
                "vpn_proxy_score": int(ip_intelligence.get("risk_score", 0)),
                "is_datacenter": bool(ip_intelligence.get("is_datacenter", False)),
                "fingerprint_reuse_count": len(visitor.get("fingerprint_hashes", [])),
                "session_count": len(visitor.get("session_ids", [])),
                "user_agent_count": len(visitor.get("user_agents", [])),
                "webdriver_detected": bool(
                    (visitor.get("automation_signals") or {}).get("webdriver", False)
                ),
                "rapid_generate_attempts": behavior_summary["rapid_generate_attempts"],
                "no_behavior_before_generate": behavior_summary["no_behavior_before_generate"],
            }
        ).as_dict()
        if risk_decision["decision"] == "BLOCK":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Too many requests. Please wait a moment and try again."},
            )
        if risk_decision["decision"] == "REQUIRE_LOGIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_build_limit_response(message="Free limit reached. Please log in to continue."),
            )
        decision = await self.fraud_decision_service.decide(
            visitor=visitor,
            request=request,
            action_type="PDF_GENERATE_ATTEMPT",
            payload=payload,
            context={"shared_usage_count": shared_used, "ip_intelligence": ip_intelligence, "ip_details": ip_details},
        )
        await self.fraud_event_service.create_from_request(
            request=request,
            visitor={**visitor, "risk_score": decision["risk_score"], "risk_level": decision["risk_level"]},
            event_type=AdminFraudEventType.FRAUD_DECISION_RECORDED.value,
            severity=_severity_for_decision(decision["decision"], decision["risk_level"]),
            action=f"Fraud decision: {decision['decision']}.",
            allowed=decision["decision"] in {"ALLOW", "ALLOW_LOG"},
            reason=_decision_reason_text(decision),
            metadata=decision,
        )
        if decision["decision"] == "REQUIRE_LOGIN":
            free_limit_reached = shared_used >= shared_limit
            await self.behavior_service.record_internal_event(
                visitor_id=visitor["_id"],
                user_id=None,
                event_type="LIMIT_REACHED",
                metadata={"reason": "REQUIRE_LOGIN"},
            )
            if free_limit_reached:
                visitor = await self.visitor_repository.mark_visitor_blocked(
                    visitor_id=visitor["_id"],
                    reason="FREE_LIMIT_REACHED",
                ) or visitor
                await self.fraud_service.create_blocked_entity(
                    entity_type=BlockedEntityType.VISITOR.value,
                    entity_value=visitor["_id"],
                    reason="FREE_LIMIT_REACHED",
                    risk_score=int(decision["risk_score"]),
                )
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=visitor,
                event_type=AdminFraudEventType.PDF_GENERATION_BLOCKED.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="PDF generation required login.",
                allowed=False,
                reason="REQUIRE_LOGIN",
                metadata={"title": payload.title, "decision": decision},
            )
            await self.fraud_decision_service.decide(
                visitor=visitor,
                request=request,
                action_type="PDF_GENERATE_BLOCKED",
                payload=payload,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_build_limit_response(),
            )
        if decision["decision"] == "BLOCK":
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=visitor,
                event_type=AdminFraudEventType.PDF_GENERATION_BLOCKED.value,
                severity=AdminFraudSeverity.CRITICAL.value,
                action="PDF generation blocked.",
                allowed=False,
                reason="CRITICAL_RISK",
                metadata={"title": payload.title, "decision": decision},
            )
            await self.fraud_decision_service.decide(
                visitor=visitor,
                request=request,
                action_type="PDF_GENERATE_BLOCKED",
                payload=payload,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_build_block_response(
                    used=int(visitor.get("free_usage_count", 0)),
                    free_limit=self.settings.FREE_USAGE_LIMIT,
                ),
            )

        if bool(visitor.get("is_blocked", False)):
            block_reason = visitor.get("block_reason") or "VISITOR_BLOCKED"
            if block_reason == "FREE_LIMIT_REACHED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_build_limit_response(),
                )
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
                detail=_build_block_response(
                    free_limit=self.settings.FREE_USAGE_LIMIT,
                    used=min(
                        int(visitor.get("free_usage_count", 0)),
                        self.settings.FREE_USAGE_LIMIT,
                    ),
                ),
            )

        if shared_used >= shared_limit:
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
                    "free_usage_count": shared_used,
                    "free_usage_limit": shared_limit,
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
                    "free_usage_count": shared_used,
                    "free_usage_limit": shared_limit,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_build_limit_response(),
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
                "ip_address": ip_address,
                "fingerprint_hash": visitor.get("primary_fingerprint_hash", ""),
                "content_hash": content_hash(payload.content),
            }
            await self.pdf_repository.create_pdf_record(pdf_data)
            updated_visitor = await self.visitor_repository.increment_free_usage(
                visitor_id=visitor["_id"]
            )
            if updated_visitor is None:
                raise RuntimeError("Visitor usage update failed")
            await self.anonymous_usage_service.record_anonymous_pdf_usage(
                ip_address=ip_address,
                visitor_id=updated_visitor["_id"],
                anon_id=anon_id,
                fingerprint_hash=fingerprint_hash,
                user_agent=user_agent,
            )
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=updated_visitor,
                event_type=AdminFraudEventType.PDF_GENERATION_ALLOWED.value,
                severity=AdminFraudSeverity.LOW.value,
                action="PDF generation allowed.",
                allowed=True,
                metadata={"pdf_id": pdf_id, "title": payload.title},
            )
            await self.behavior_service.record_internal_event(
                visitor_id=updated_visitor["_id"],
                user_id=None,
                event_type="PDF_GENERATED",
                metadata={"pdf_id": pdf_id, "content_hash": content_hash(payload.content)},
            )
            await self.fraud_decision_service.decide(
                visitor=updated_visitor,
                request=request,
                action_type="PDF_GENERATE_ALLOWED",
                payload=payload,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Anonymous PDF generation failed visitor_id=%s ip=%s has_anon_id=%s has_fingerprint=%s",
                visitor.get("_id"),
                ip_address,
                bool(request.headers.get("X-Anon-Id") or get_visitor_cookie(request.cookies)),
                bool(request.headers.get("X-Device-Fingerprint")),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Too many requests. Please wait a moment and try again.",
            ) from exc

        visitor_usage_after = int((updated_visitor or visitor).get("free_usage_count", 0))
        ip_usage_after = int(shared_usage_snapshot["ip_usage_count"]) + 1
        shared_usage_after = max(visitor_usage_after, ip_usage_after)
        remaining_after = max(shared_limit - shared_usage_after, 0)
        return PDFGenerateResponse(
            success=True,
            message="PDF generated successfully.",
            pdf_id=pdf_id,
            title=payload.title,
            file_name=file_name,
            free_limit=shared_limit,
            used=shared_usage_after,
            remaining=remaining_after,
            free_usage_count=shared_usage_after,
            free_usage_limit=shared_limit,
            remaining_free_uses=remaining_after,
            requires_login=shared_usage_after >= shared_limit,
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
        if visitor is not None:
            decision = await self.fraud_decision_service.decide(
                visitor=visitor,
                request=request,
                action_type="PDF_GENERATE_ATTEMPT",
                user=current_user,
                payload=payload,
            )
            if decision["decision"] == "ALLOW_LOG":
                await self.fraud_event_service.create_from_request(
                    request=request,
                    visitor={**visitor, "risk_score": decision["risk_score"], "risk_level": decision["risk_level"]},
                    event_type=AdminFraudEventType.FRAUD_DECISION_RECORDED.value,
                    severity=_severity_for_decision(decision["decision"], decision["risk_level"]),
                    action="Logged-in generation allowed with admin review signal.",
                    allowed=True,
                    reason=_decision_reason_text(decision),
                    metadata=decision,
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
                "ip_address": normalize_ip(client_ip(request)),
                "fingerprint_hash": (
                    visitor.get("primary_fingerprint_hash")
                    if visitor is not None
                    else None
                ),
                "content_hash": content_hash(payload.content),
            }
            await self.pdf_repository.create_pdf_record(pdf_data)
            usage = await self.user_usage_service.increment_after_generation(current_user)
            await self.behavior_service.record_internal_event(
                visitor_id=visitor["_id"] if visitor is not None else None,
                user_id=current_user["_id"],
                event_type="PDF_GENERATED",
                metadata={"pdf_id": pdf_id, "content_hash": content_hash(payload.content)},
            )
            if visitor is not None:
                await self.fraud_decision_service.decide(
                    visitor=visitor,
                    request=request,
                    action_type="PDF_GENERATE_ALLOWED",
                    user=current_user,
                    payload=payload,
                    normal_flow=True,
                )
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
            await self._record_download_decision(request, current_user, await self._get_optional_visitor_from_request(request))
            return pdf_record

        visitor = await self._get_optional_visitor_from_request(request)
        if (
            current_user is None
            and visitor is not None
            and pdf_record.get("visitor_id") == visitor["_id"]
            and not pdf_record.get("user_id")
        ):
            await self._record_download_decision(request, None, visitor)
            return pdf_record

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="PDF not found.")

    async def _record_download_decision(
        self,
        request: Request,
        current_user: dict[str, Any] | None,
        visitor: dict[str, Any] | None,
    ) -> None:
        if visitor is None:
            return
        await self.fraud_decision_service.decide(
            visitor=visitor,
            request=request,
            action_type="DOWNLOAD",
            user=current_user,
            normal_flow=True,
        )

    async def _get_visitor_from_request(self, request: Request) -> dict[str, Any]:
        visitor = await self.visitor_service.find_visitor_from_request(request)
        if visitor is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="We could not start your session. Please refresh and try again.",
            )
        return visitor

    async def _get_optional_visitor_from_request(
        self,
        request: Request,
    ) -> dict[str, Any] | None:
        return await self.visitor_service.find_visitor_from_request(request)

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
                        "ip_address": normalize_ip(client_ip(request)),
                        "user_agent": request.headers.get("user-agent"),
                    },
                }
            ],
        )

    async def _behavior_summary(self, visitor_id: str) -> dict[str, bool]:
        recent_generate_clicks = await self.behavior_service.repository.count_by_visitor(
            visitor_id,
            event_type="GENERATE_CLICKED",
            since=utc_now() - timedelta(seconds=60),
        )
        page_views = await self.behavior_service.repository.count_by_visitor(
            visitor_id,
            event_type="PAGE_VIEW",
        )
        return {
            "rapid_generate_attempts": recent_generate_clicks > 10,
            "no_behavior_before_generate": page_views == 0,
        }


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


def _build_limit_response(
    message: str = "Free limit reached. Please log in to continue.",
) -> dict[str, bool | str]:
    return {
        "success": False,
        "message": message,
        "requires_login": True,
    }


def _build_block_response(free_limit: int, used: int) -> dict[str, bool | str]:
    return {
        "success": False,
        "message": "We could not process this request right now. Please try again later.",
    }


def _severity_for_decision(decision: str, risk_level: str) -> str:
    if decision == "BLOCK" or risk_level == "CRITICAL":
        return AdminFraudSeverity.CRITICAL.value
    if decision == "REQUIRE_LOGIN" or risk_level == "HIGH":
        return AdminFraudSeverity.HIGH.value
    if decision == "ALLOW_LOG" or risk_level == "MEDIUM":
        return AdminFraudSeverity.MEDIUM.value
    return AdminFraudSeverity.LOW.value


def _decision_reason_text(decision: dict[str, Any]) -> str | None:
    reasons = decision.get("reasons") or []
    if not reasons:
        return None
    values: list[str] = []
    for reason in reasons:
        if isinstance(reason, dict):
            values.append(str(reason.get("message") or reason.get("code") or reason))
        else:
            values.append(str(reason))
    return "; ".join(values)
