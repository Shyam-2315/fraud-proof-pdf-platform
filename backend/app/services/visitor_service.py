from typing import Any

from fastapi import Request

from app.config import get_settings
from app.core.public_config import get_visitor_cookie
from app.models.fraud import BlockedEntityType, FraudEventType, FraudSeverity
from app.models.fraud_event import (
    FraudEventType as AdminFraudEventType,
    FraudSeverity as AdminFraudSeverity,
)
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.visitor import VisitorIdentifyRequest
from app.services.fraud_event_service import FraudEventService
from app.services.fraud_service import FraudService, calculate_risk_level
from app.utils.security import (
    generate_uuid,
    normalize_ip,
    safe_append_unique,
    utc_now,
)


class VisitorService:
    def __init__(
        self,
        repository: VisitorRepository | None = None,
        fraud_service: FraudService | None = None,
        fraud_event_service: FraudEventService | None = None,
    ) -> None:
        self.repository = repository or VisitorRepository()
        self.fraud_service = fraud_service or FraudService()
        self.fraud_event_service = fraud_event_service or FraudEventService()

    async def identify_visitor(
        self,
        request: Request,
        payload: VisitorIdentifyRequest,
    ) -> tuple[dict[str, Any], bool, str]:
        request_cookie_id = get_visitor_cookie(request.cookies)
        generated_cookie_id = request_cookie_id or generate_uuid()
        current_ip = normalize_ip(request.client.host if request.client else "")
        current_user_agent = request.headers.get("user-agent", "")
        request_headers = dict(request.headers)
        now = utc_now()

        visitor = await self.repository.find_best_match(
            cookie_id=request_cookie_id,
            local_storage_id=payload.local_storage_id,
            session_id=payload.session_id,
            fingerprint_hash=payload.fingerprint_hash,
        )

        if visitor is None:
            blocked_fingerprint = await self.fraud_service.is_fingerprint_blocked(
                payload.fingerprint_hash
            )
            is_blocked = blocked_fingerprint is not None
            risk_score = int(blocked_fingerprint.get("risk_score", 100)) if is_blocked else 0
            visitor_data = {
                "_id": generate_uuid(),
                "cookie_id": generated_cookie_id,
                "local_storage_ids": safe_append_unique([], payload.local_storage_id),
                "session_ids": safe_append_unique([], payload.session_id),
                "fingerprint_hashes": safe_append_unique([], payload.fingerprint_hash),
                "primary_fingerprint_hash": payload.fingerprint_hash,
                "ip_addresses": safe_append_unique([], current_ip),
                "user_agents": safe_append_unique([], current_user_agent),
                "device_info": payload.device_info.model_dump(),
                "free_usage_count": 0,
                "risk_score": risk_score,
                "risk_level": calculate_risk_level(risk_score),
                "is_blocked": is_blocked,
                "block_reason": "FINGERPRINT_BLOCKED" if is_blocked else None,
                "created_at": now,
                "last_seen_at": now,
            }
            created_visitor = await self.repository.create_visitor(visitor_data)
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=created_visitor,
                event_type=AdminFraudEventType.VISITOR_IDENTIFIED.value,
                severity=AdminFraudSeverity.LOW.value,
                action="Anonymous visitor identified.",
                allowed=not is_blocked,
                reason=created_visitor.get("block_reason"),
                metadata={"is_new_visitor": True},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
            if is_blocked:
                await self.fraud_service.create_fraud_events(
                    created_visitor["_id"],
                    [
                        {
                            "event_type": FraudEventType.SUSPICIOUS_REIDENTIFICATION.value,
                            "severity": FraudSeverity.HIGH.value,
                            "risk_points": 40,
                            "message": "Blocked fingerprint attempted reidentification.",
                            "signals": _build_signals(
                                cookie_id=request_cookie_id,
                                local_storage_id=payload.local_storage_id,
                                session_id=payload.session_id,
                                fingerprint_hash=payload.fingerprint_hash,
                                ip_address=current_ip,
                                user_agent=current_user_agent,
                            ),
                        }
                    ],
                )
            return created_visitor, True, generated_cookie_id

        is_new_session = payload.session_id not in visitor.get("session_ids", [])
        is_new_fingerprint = payload.fingerprint_hash not in visitor.get(
            "fingerprint_hashes",
            [],
        )
        risk_evaluation = self.fraud_service.evaluate_reidentification_risk(
            visitor=visitor,
            cookie_id=request_cookie_id,
            local_storage_id=payload.local_storage_id,
            session_id=payload.session_id,
            fingerprint_hash=payload.fingerprint_hash,
            ip_address=current_ip,
            user_agent=current_user_agent,
            headers=request_headers,
        )
        updated_risk_score = min(
            int(visitor.get("risk_score", 0)) + int(risk_evaluation["risk_points"]),
            100,
        )
        cookie_id = visitor.get("cookie_id") or generated_cookie_id
        update_data = {
            "cookie_id": cookie_id,
            "local_storage_ids": safe_append_unique(
                visitor.get("local_storage_ids", []), payload.local_storage_id
            ),
            "session_ids": safe_append_unique(
                visitor.get("session_ids", []), payload.session_id
            ),
            "fingerprint_hashes": safe_append_unique(
                visitor.get("fingerprint_hashes", []), payload.fingerprint_hash
            ),
            "ip_addresses": safe_append_unique(
                visitor.get("ip_addresses", []), current_ip
            ),
            "user_agents": safe_append_unique(
                visitor.get("user_agents", []), current_user_agent
            ),
            "device_info": payload.device_info.model_dump(),
            "risk_score": updated_risk_score,
            "risk_level": calculate_risk_level(updated_risk_score),
            "last_seen_at": now,
        }
        updated_visitor = await self.repository.update_visitor(
            visitor_id=visitor["_id"],
            update_data=update_data,
        )
        await self.fraud_service.create_fraud_events(
            visitor_id=visitor["_id"],
            events=risk_evaluation["events"],
        )
        final_visitor = updated_visitor or {**visitor, **update_data}
        await self.fraud_event_service.create_from_request(
            request=request,
            visitor=final_visitor,
            event_type=AdminFraudEventType.VISITOR_IDENTIFIED.value,
            severity=AdminFraudSeverity.LOW.value,
            action="Anonymous visitor identified.",
            allowed=not bool(final_visitor.get("is_blocked", False)),
            reason=final_visitor.get("block_reason"),
            metadata={"is_new_visitor": False},
            local_storage_id=payload.local_storage_id,
            session_id=payload.session_id,
            fingerprint_hash=payload.fingerprint_hash,
        )
        if not request_cookie_id:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.COOKIE_MISSING.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="Existing visitor matched without cookie.",
                allowed=True,
                reason="Cookie missing on visitor identify.",
                metadata={"matched_visitor_id": visitor["_id"]},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
        if is_new_session:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.NEW_SESSION_LINKED.value,
                severity=AdminFraudSeverity.LOW.value,
                action="New session linked to existing visitor.",
                allowed=True,
                metadata={"session_id_count": len(final_visitor.get("session_ids", []))},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
        if is_new_fingerprint:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.NEW_FINGERPRINT_LINKED.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="New fingerprint linked to existing visitor.",
                allowed=True,
                metadata={
                    "fingerprint_hash_count": len(
                        final_visitor.get("fingerprint_hashes", [])
                    )
                },
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
        if len(final_visitor.get("session_ids", [])) > 3:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.MULTIPLE_SESSIONS_DETECTED.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="Multiple sessions detected for visitor.",
                allowed=True,
                metadata={"session_id_count": len(final_visitor.get("session_ids", []))},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )

        if bool(risk_evaluation["should_block_fingerprint"]):
            await self.fraud_service.create_blocked_entity(
                entity_type=BlockedEntityType.FINGERPRINT.value,
                entity_value=payload.fingerprint_hash,
                reason="HIGH_RISK_FINGERPRINT",
                risk_score=updated_risk_score,
            )
            blocked_visitor = await self.repository.mark_visitor_blocked(
                visitor_id=visitor["_id"],
                reason="HIGH_RISK_FINGERPRINT",
            )
            if blocked_visitor is not None:
                updated_visitor = blocked_visitor
                final_visitor = blocked_visitor
                await self.fraud_event_service.create_from_request(
                    request=request,
                    visitor=blocked_visitor,
                    event_type=AdminFraudEventType.VISITOR_BLOCKED.value,
                    severity=AdminFraudSeverity.HIGH.value,
                    action="Visitor blocked.",
                    allowed=False,
                    reason="HIGH_RISK_FINGERPRINT",
                    metadata={"risk_score": updated_risk_score},
                    local_storage_id=payload.local_storage_id,
                    session_id=payload.session_id,
                    fingerprint_hash=payload.fingerprint_hash,
                )

        return final_visitor, False, cookie_id


def build_usage_summary(visitor: dict[str, Any]) -> dict[str, int]:
    settings = get_settings()
    free_usage_count = int(visitor.get("free_usage_count", 0))
    return {
        "free_usage_count": free_usage_count,
        "free_usage_limit": settings.FREE_USAGE_LIMIT,
        "remaining_free_uses": max(settings.FREE_USAGE_LIMIT - free_usage_count, 0),
    }


def _build_signals(
    cookie_id: str | None,
    local_storage_id: str | None,
    session_id: str | None,
    fingerprint_hash: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> dict[str, str | None]:
    return {
        "cookie_id": cookie_id,
        "local_storage_id": local_storage_id,
        "session_id": session_id,
        "fingerprint_hash": fingerprint_hash,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
