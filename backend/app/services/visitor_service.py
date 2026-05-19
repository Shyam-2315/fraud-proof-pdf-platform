from typing import Any

from fastapi import Request

from app.config import get_settings
from app.models.fraud import BlockedEntityType, FraudEventType, FraudSeverity
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.visitor import VisitorIdentifyRequest
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
    ) -> None:
        self.repository = repository or VisitorRepository()
        self.fraud_service = fraud_service or FraudService()

    async def identify_visitor(
        self,
        request: Request,
        payload: VisitorIdentifyRequest,
    ) -> tuple[dict[str, Any], bool, str]:
        request_cookie_id = request.cookies.get("anon_id")
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

        return updated_visitor or {**visitor, **update_data}, False, cookie_id


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
