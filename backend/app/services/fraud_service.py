from typing import Any

from app.config import get_settings
from app.models.fraud import BlockedEntityType, FraudEventType, FraudSeverity
from app.repositories.fraud_repository import FraudRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.fraud import FraudEventResponse, FraudSummaryResponse
from app.utils.security import generate_uuid, safe_append_unique, utc_now


class FraudService:
    def __init__(
        self,
        fraud_repository: FraudRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
    ) -> None:
        self.settings = get_settings()
        self.fraud_repository = fraud_repository or FraudRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()

    def calculate_risk_level(self, score: int) -> str:
        return calculate_risk_level(score)

    def detect_vpn_proxy_placeholder(
        self,
        ip_address: str,
        headers: dict[str, str],
    ) -> bool:
        return detect_vpn_proxy_placeholder(ip_address, headers)

    def evaluate_reidentification_risk(
        self,
        visitor: dict[str, Any] | None,
        cookie_id: str | None,
        local_storage_id: str,
        session_id: str,
        fingerprint_hash: str,
        ip_address: str,
        user_agent: str,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        if visitor is None:
            return {
                "risk_points": 0,
                "risk_level": calculate_risk_level(0),
                "events": events,
                "should_block_fingerprint": False,
            }

        signals = _build_signals(
            cookie_id=cookie_id,
            local_storage_id=local_storage_id,
            session_id=session_id,
            fingerprint_hash=fingerprint_hash,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if (
            not cookie_id
            and fingerprint_hash
            and fingerprint_hash in visitor.get("fingerprint_hashes", [])
        ):
            events.append(
                _event(
                    FraudEventType.COOKIE_MISSING_BUT_FINGERPRINT_MATCHED,
                    FraudSeverity.MEDIUM,
                    25,
                    "Cookie missing but existing fingerprint matched.",
                    signals,
                )
            )

        if local_storage_id not in visitor.get("local_storage_ids", []):
            events.append(
                _event(
                    FraudEventType.LOCAL_STORAGE_CHANGED,
                    FraudSeverity.LOW,
                    15,
                    "Local storage identifier changed for existing visitor.",
                    signals,
                )
            )

        if session_id not in visitor.get("session_ids", []):
            events.append(
                _event(
                    FraudEventType.SESSION_CHANGED,
                    FraudSeverity.LOW,
                    5,
                    "Session identifier changed for existing visitor.",
                    signals,
                )
            )

        if ip_address and ip_address not in visitor.get("ip_addresses", []):
            events.append(
                _event(
                    FraudEventType.NEW_IP_FOR_FINGERPRINT,
                    FraudSeverity.MEDIUM,
                    20,
                    "New IP address observed for existing fingerprint.",
                    signals,
                )
            )

        updated_ips = safe_append_unique(visitor.get("ip_addresses", []), ip_address)
        if len(updated_ips) >= 3:
            events.append(
                _event(
                    FraudEventType.MULTIPLE_IPS_DETECTED,
                    FraudSeverity.MEDIUM,
                    25,
                    "Multiple IP addresses detected for visitor.",
                    signals,
                )
            )

        updated_sessions = safe_append_unique(visitor.get("session_ids", []), session_id)
        if len(updated_sessions) >= 5:
            events.append(
                _event(
                    FraudEventType.TOO_MANY_SESSIONS,
                    FraudSeverity.MEDIUM,
                    20,
                    "Too many session identifiers detected for visitor.",
                    signals,
                )
            )

        if detect_vpn_proxy_placeholder(ip_address, headers):
            events.append(
                _event(
                    FraudEventType.VPN_PROXY_SUSPECTED,
                    FraudSeverity.HIGH,
                    30,
                    "VPN or proxy indicators detected in request headers.",
                    signals,
                )
            )

        if int(visitor.get("free_usage_count", 0)) >= self.settings.FREE_USAGE_LIMIT:
            events.append(
                _event(
                    FraudEventType.FREE_LIMIT_REACHED,
                    FraudSeverity.HIGH,
                    40,
                    "Anonymous free usage limit already reached.",
                    signals,
                )
            )

        risk_points = sum(int(event["risk_points"]) for event in events)
        final_risk_score = min(int(visitor.get("risk_score", 0)) + risk_points, 100)
        return {
            "risk_points": risk_points,
            "risk_level": calculate_risk_level(final_risk_score),
            "events": events,
            "should_block_fingerprint": final_risk_score >= 90,
        }

    async def create_fraud_events(
        self,
        visitor_id: str | None,
        events: list[dict[str, Any]],
    ) -> None:
        for event in events:
            await self.fraud_repository.create_fraud_event(
                {
                    "_id": generate_uuid(),
                    "visitor_id": visitor_id,
                    "event_type": event["event_type"],
                    "severity": event["severity"],
                    "risk_points": event["risk_points"],
                    "message": event["message"],
                    "signals": event["signals"],
                    "created_at": utc_now(),
                }
            )

    async def create_blocked_entity(
        self,
        entity_type: str,
        entity_value: str,
        reason: str,
        risk_score: int,
    ) -> dict[str, Any] | None:
        existing = await self.fraud_repository.find_active_blocked_entity(
            entity_type=entity_type,
            entity_value=entity_value,
        )
        if existing is not None:
            return existing

        return await self.fraud_repository.create_blocked_entity(
            {
                "_id": generate_uuid(),
                "entity_type": entity_type,
                "entity_value": entity_value,
                "reason": reason,
                "risk_score": risk_score,
                "created_at": utc_now(),
                "expires_at": None,
                "is_active": True,
            }
        )

    async def get_fraud_summary(self) -> FraudSummaryResponse:
        recent_events = await self.fraud_repository.list_fraud_events(limit=10)
        return FraudSummaryResponse(
            total_visitors=await self.visitor_repository.count_visitors(),
            blocked_visitors=await self.visitor_repository.count_blocked_visitors(),
            total_fraud_events=await self.fraud_repository.count_fraud_events(),
            high_risk_visitors=await self.visitor_repository.count_high_risk_visitors(),
            blocked_entities=await self.fraud_repository.count_blocked_entities(),
            recent_events=[build_fraud_event_response(event) for event in recent_events],
        )

    async def is_fingerprint_blocked(
        self,
        fingerprint_hash: str,
    ) -> dict[str, Any] | None:
        return await self.fraud_repository.find_active_blocked_entity(
            entity_type=BlockedEntityType.FINGERPRINT.value,
            entity_value=fingerprint_hash,
        )


def calculate_risk_level(score: int) -> str:
    if score <= 39:
        return "LOW"
    if score <= 69:
        return "MEDIUM"
    return "HIGH"


def detect_vpn_proxy_placeholder(ip_address: str, headers: dict[str, str]) -> bool:
    del ip_address
    normalized_headers = {key.lower(): value for key, value in headers.items()}
    forwarded_for = normalized_headers.get("x-forwarded-for", "")
    if "," in forwarded_for:
        return True
    if normalized_headers.get("via"):
        return True
    if normalized_headers.get("x-proxy-id"):
        return True
    if normalized_headers.get("x-vpn"):
        return True
    return normalized_headers.get("cf-ipcountry", "").upper() == "T1"


def build_fraud_event_response(event: dict[str, Any]) -> FraudEventResponse:
    return FraudEventResponse(
        event_id=event["_id"],
        visitor_id=event.get("visitor_id"),
        event_type=event.get("event_type", ""),
        severity=event.get("severity", ""),
        risk_points=int(event.get("risk_points", 0)),
        message=event.get("message", ""),
        signals=event.get("signals", {}),
        created_at=event["created_at"],
    )


def _event(
    event_type: FraudEventType,
    severity: FraudSeverity,
    risk_points: int,
    message: str,
    signals: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_type": event_type.value,
        "severity": severity.value,
        "risk_points": risk_points,
        "message": message,
        "signals": signals,
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
