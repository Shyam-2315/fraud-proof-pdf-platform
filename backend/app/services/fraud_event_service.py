from typing import Any

from fastapi import Request

from app.core.public_config import get_visitor_cookie
from app.models.fraud_event import FraudEventType, FraudSeverity
from app.repositories.fraud_event_repository import FraudEventRepository
from app.schemas.fraud_event import FraudEventItem
from app.utils.request_utils import get_client_ip
from app.utils.security import generate_uuid, normalize_ip, utc_now

class FraudEventService:
    def __init__(
        self,
        repository: FraudEventRepository | None = None,
    ) -> None:
        self.repository = repository or FraudEventRepository()

    async def create_event(
        self,
        visitor_id: str | None,
        event_type: str,
        severity: str = FraudSeverity.LOW.value,
        action: str = "",
        allowed: bool = True,
        reason: str | None = None,
        risk_score: int = 0,
        risk_level: str = "LOW",
        fingerprint_hash: str | None = None,
        local_storage_id: str | None = None,
        session_id: str | None = None,
        cookie_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = generate_uuid()
        event_data = {
            "_id": event_id,
            "id": event_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "severity": severity,
            "action": action or event_type,
            "allowed": allowed,
            "reason": reason,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "fingerprint_hash": fingerprint_hash,
            "local_storage_id": local_storage_id,
            "session_id": session_id,
            "cookie_id": cookie_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "created_at": utc_now(),
        }
        return await self.repository.create(event_data)

    async def create_from_request(
        self,
        request: Request,
        visitor: dict[str, Any],
        event_type: str,
        severity: str = FraudSeverity.LOW.value,
        action: str = "",
        allowed: bool = True,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        local_storage_id: str | None = None,
        session_id: str | None = None,
        fingerprint_hash: str | None = None,
    ) -> dict[str, Any]:
        return await self.create_event(
            visitor_id=visitor.get("_id"),
            event_type=event_type,
            severity=severity,
            action=action,
            allowed=allowed,
            reason=reason,
            risk_score=int(visitor.get("risk_score", 0)),
            risk_level=str(visitor.get("risk_level", "LOW")),
            fingerprint_hash=(
                fingerprint_hash
                or request.headers.get("x-device-fingerprint")
                or visitor.get("primary_fingerprint_hash")
            ),
            local_storage_id=(
                local_storage_id
                or request.headers.get("x-visitor-id")
                or _last_or_none(visitor.get("local_storage_ids", []))
            ),
            session_id=(
                session_id
                or request.headers.get("x-session-id")
                or _last_or_none(visitor.get("session_ids", []))
            ),
            cookie_id=get_visitor_cookie(request.cookies) or visitor.get("cookie_id"),
            ip_address=normalize_ip(get_client_ip(request)),
            user_agent=request.headers.get("user-agent"),
            metadata=metadata,
        )


def build_fraud_event_item(event: dict[str, Any]) -> FraudEventItem:
    signals = event.get("signals", {})
    metadata = dict(event.get("metadata", {}))
    if event.get("message") and "message" not in metadata:
        metadata["message"] = event.get("message")
    if event.get("risk_points") is not None and "risk_points" not in metadata:
        metadata["risk_points"] = event.get("risk_points")

    return FraudEventItem(
        id=str(event.get("id") or event.get("_id") or ""),
        visitor_id=event.get("visitor_id"),
        event_type=str(event.get("event_type", "")),
        severity=str(event.get("severity", FraudSeverity.LOW.value)),
        action=str(event.get("action") or event.get("event_type", "")),
        allowed=bool(event.get("allowed", True)),
        reason=event.get("reason"),
        risk_score=int(event.get("risk_score", 0)),
        risk_level=str(event.get("risk_level", "LOW")),
        fingerprint_hash=event.get("fingerprint_hash") or signals.get("fingerprint_hash"),
        local_storage_id=event.get("local_storage_id") or signals.get("local_storage_id"),
        session_id=event.get("session_id") or signals.get("session_id"),
        cookie_id=event.get("cookie_id") or signals.get("cookie_id"),
        ip_address=event.get("ip_address") or signals.get("ip_address"),
        user_agent=event.get("user_agent") or signals.get("user_agent"),
        metadata=metadata,
        created_at=event["created_at"],
    )


def _last_or_none(values: list[Any]) -> Any:
    return values[-1] if values else None
