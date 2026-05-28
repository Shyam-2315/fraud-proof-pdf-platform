from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request

from app.models.behavior import BehaviorEventType
from app.models.fraud_event import FraudEventType, FraudSeverity
from app.models.risk import RiskLevel
from app.repositories.behavior_repository import BehaviorEventRepository
from app.repositories.fraud_event_repository import FraudEventRepository
from app.repositories.risk_repository import RiskScoreSnapshotRepository
from app.repositories.user_repository import UserRepository
from app.repositories.visitor_repository import VisitorRepository
from app.services.fraud_event_service import FraudEventService
from app.services.ip_intelligence_service import IPIntelligenceService
from app.services.rate_limit_service import client_ip
from app.utils.security import generate_uuid, utc_now


class RiskScoringService:
    """
    Service that coordinates domain workflows and business rules.
    """
    def __init__(
        self,
        visitor_repository: VisitorRepository | None = None,
        user_repository: UserRepository | None = None,
        behavior_repository: BehaviorEventRepository | None = None,
        fraud_event_repository: FraudEventRepository | None = None,
        snapshot_repository: RiskScoreSnapshotRepository | None = None,
        fraud_event_service: FraudEventService | None = None,
        ip_intelligence_service: IPIntelligenceService | None = None,
    ) -> None:
        """
        Initialize the service with optional collaborators and runtime dependencies.
        
        Args:
            visitor_repository: The visitor repository value used by this operation.
            user_repository: The user repository value used by this operation.
            behavior_repository: The behavior repository value used by this operation.
            fraud_event_repository: The fraud event repository value used by this operation.
            snapshot_repository: The snapshot repository value used by this operation.
            fraud_event_service: The fraud event service value used by this operation.
            ip_intelligence_service: The ip intelligence service value used by this operation.
        
        Returns:
            None.
        """
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.user_repository = user_repository or UserRepository()
        self.behavior_repository = behavior_repository or BehaviorEventRepository()
        self.fraud_event_repository = fraud_event_repository or FraudEventRepository()
        self.snapshot_repository = snapshot_repository or RiskScoreSnapshotRepository()
        self.fraud_event_service = fraud_event_service or FraudEventService()
        self.ip_intelligence_service = ip_intelligence_service or IPIntelligenceService()

    async def score_visitor(
        self,
        visitor: dict[str, Any],
        request: Request | None = None,
        action_type: str = "IDENTIFY",
        payload: Any | None = None,
        context: dict[str, Any] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Score Visitor for the requested operation.
        
        Args:
            visitor: Visitor record involved in the operation.
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
            action_type: The action type value used by this operation.
            payload: Validated request payload for this operation.
            context: Additional contextual data that influences the operation.
            user: User record involved in the operation.
        
        Returns:
            Operation result represented as `dict[str, Any]`.
        """
        context = context or {}
        reasons: list[str] = []
        signals: dict[str, Any] = {"action_type": action_type}
        score = 0
        now = utc_now()
        ip_address = client_ip(request) if request is not None else _last(visitor.get("ip_addresses", []))
        headers = dict(request.headers) if request is not None else {}
        user_agent = headers.get("user-agent", _last(visitor.get("user_agents", [])) or "")
        automation_signals = _automation_signals(visitor, payload, context)

        def add(points: int, reason: str, **extra: Any) -> None:
            """
            Add for the requested operation.
            
            Args:
                points: The points value used by this operation.
                reason: The reason value used by this operation.
                **extra: The extra value used by this operation.
            
            Returns:
                None.
            """
            nonlocal score
            score += points
            reasons.append(reason)
            signals.update(extra)

        cookie_ids = _unique(visitor.get("cookie_ids", []) + [visitor.get("cookie_id")])
        session_ids = _unique(visitor.get("session_ids", []))
        ip_addresses = _unique(visitor.get("ip_addresses", []))

        if context.get("cookie_missing_after_seen"):
            add(15, "Cookie missing after a previous cookie existed.")
        if len(cookie_ids) > 1:
            add(30, "Same fingerprint was seen with multiple cookie IDs.", cookie_id_count=len(cookie_ids))
        if visitor.get("local_storage_ids") and len(session_ids) > 3:
            add(20, "Same local storage ID has many session IDs.", session_id_count=len(session_ids))
        if _count_recent_unique(visitor.get("session_observations", []), now - timedelta(minutes=10)) > 3:
            add(20, "More than 3 sessions were seen in 10 minutes.")
        if _count_recent_unique(visitor.get("ip_observations", []), now - timedelta(minutes=30)) > 3:
            add(25, "More than 3 IPs were seen in 30 minutes.")

        ip_intel = await self.ip_intelligence_service.check_ip(ip_address)
        signals["ip_intelligence"] = _public_ip_intel(ip_intel)
        if ip_intel.get("is_tor"):
            add(50, "TOR exit IP detected.", ip_address=ip_address)
            await self._admin_signal_event(visitor, FraudEventType.VPN_PROXY_DETECTED.value, FraudSeverity.CRITICAL.value, "TOR IP detected.", ip_intel)
        elif ip_intel.get("is_vpn") or ip_intel.get("is_proxy") or ip_intel.get("is_datacenter"):
            add(30, "VPN, proxy, or datacenter IP detected.", ip_address=ip_address)
            await self._admin_signal_event(visitor, FraudEventType.VPN_PROXY_DETECTED.value, FraudSeverity.HIGH.value, "VPN/proxy/datacenter IP detected.", ip_intel)

        if bool(automation_signals.get("webdriver")):
            add(40, "navigator.webdriver was true.", webdriver=True)
            await self._admin_signal_event(visitor, FraudEventType.AUTOMATION_SIGNAL_DETECTED.value, FraudSeverity.HIGH.value, "navigator.webdriver true.", automation_signals)
        if _headless_user_agent(user_agent) or bool(automation_signals.get("headless")):
            add(50, "Headless browser indicators detected.", user_agent=user_agent)
            await self._admin_signal_event(visitor, FraudEventType.HEADLESS_BROWSER_SUSPECTED.value, FraudSeverity.HIGH.value, "Headless browser suspected.", automation_signals)
        if _zero_plugins_in_browser(user_agent, automation_signals):
            add(50, "Browser-like client reported zero plugins.", plugins_count=automation_signals.get("plugins_count"))
            await self._admin_signal_event(visitor, FraudEventType.AUTOMATION_SIGNAL_DETECTED.value, FraudSeverity.HIGH.value, "Zero plugins in browser context.", automation_signals)

        first_seen = visitor.get("created_at")
        first_seen = _aware(first_seen)
        if action_type == "PDF_GENERATE" and first_seen is not None and (now - first_seen).total_seconds() < 2:
            add(25, "PDF generation happened too quickly after first visit.")

        blocked_attempts = await self.fraud_event_repository.count_events(
            {"visitor_id": visitor["_id"], "event_type": FraudEventType.PDF_GENERATION_BLOCKED.value}
        )
        if blocked_attempts > 1:
            add(30, "Multiple blocked attempts were recorded.", blocked_attempts=blocked_attempts)

        fingerprint_hash = visitor.get("primary_fingerprint_hash")
        device_profile_hash = _last(visitor.get("device_profile_hashes", []))
        account_count = await self.user_repository.count_recent_by_device(
            fingerprint_hash=fingerprint_hash,
            device_profile_hash=device_profile_hash,
            hours=24,
        )
        if account_count > 3:
            add(40, "Many accounts were created from the same fingerprint or device.", account_count=account_count)

        if await self.visitor_repository.count_by_ip(ip_address) > 10:
            add(25, "Many visitors were seen from the same IP.", ip_address=ip_address)
        if context.get("cleared_cookie_same_fingerprint"):
            add(35, "Cookie was cleared but the same fingerprint matched an existing visitor.")

        if action_type == "PDF_GENERATE":
            await self._score_behavior(visitor, payload, add)

        score = min(score, 100)
        level = calculate_risk_level(score)
        snapshot_id = generate_uuid()
        snapshot = await self.snapshot_repository.create(
            {
                "_id": snapshot_id,
                "id": snapshot_id,
                "visitor_id": visitor["_id"],
                "score": score,
                "level": level,
                "reasons": reasons,
                "signals": signals,
                "created_at": now,
            }
        )
        await self.visitor_repository.update_visitor(
            visitor_id=visitor["_id"],
            update_data={
                "risk_score": score,
                "risk_level": level,
                "risk_reasons": reasons,
                "last_risk_signals": signals,
                "last_seen_at": now,
            },
        )
        await self.fraud_event_service.create_event(
            visitor_id=visitor["_id"],
            event_type=FraudEventType.RISK_SCORE_UPDATED.value,
            severity=_severity_for_level(level),
            action="Risk score updated.",
            allowed=True,
            reason="; ".join(reasons) if reasons else "No elevated risk signals.",
            risk_score=score,
            risk_level=level,
            fingerprint_hash=fingerprint_hash,
            local_storage_id=_last(visitor.get("local_storage_ids", [])),
            session_id=_last(visitor.get("session_ids", [])),
            cookie_id=visitor.get("cookie_id"),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reasons": reasons, "signals": signals, "snapshot_id": snapshot_id},
        )
        return snapshot

    async def _score_behavior(
        self,
        visitor: dict[str, Any],
        payload: Any | None,
        add: Any,
    ) -> None:
        """
        Score Behavior for the requested operation.
        
        Args:
            visitor: Visitor record involved in the operation.
            payload: Validated request payload for this operation.
            add: The add value used by this operation.
        
        Returns:
            None.
        """
        now = utc_now()
        first_event = await self.behavior_repository.first_event(visitor["_id"])
        event_count = await self.behavior_repository.count_by_visitor(visitor["_id"])
        if event_count == 0:
            add(30, "API generation occurred without prior page or behavior activity.")
            await self._admin_signal_event(visitor, FraudEventType.API_ONLY_USAGE_PATTERN.value, FraudSeverity.HIGH.value, "API-only usage pattern.", {})
        first_event_created_at = _aware(first_event["created_at"]) if first_event is not None else None
        if first_event_created_at is not None and (now - first_event_created_at).total_seconds() < 2:
            add(25, "Generate was clicked less than 2 seconds after first activity.")
        recent_generates = await self.behavior_repository.count_by_visitor(
            visitor["_id"],
            event_type=BehaviorEventType.GENERATE_CLICKED.value,
            since=now - timedelta(seconds=30),
        )
        if recent_generates > 3:
            add(20, "Multiple generate attempts occurred within 30 seconds.")
            await self._admin_signal_event(visitor, FraudEventType.RAPID_GENERATION_ATTEMPT.value, FraudSeverity.MEDIUM.value, "Rapid generation attempts.", {"recent_generates": recent_generates})
        content_hash = getattr(payload, "content_hash", None)
        if content_hash is None and getattr(payload, "content", None):
            from app.services.behavior_service import content_hash as hash_content

            content_hash = hash_content(getattr(payload, "content"))
        same_content = await self.behavior_repository.count_same_content(
            visitor["_id"],
            content_hash,
            since=now - timedelta(hours=1),
        )
        if same_content > 2:
            add(20, "Same content was generated repeatedly.")

    async def _admin_signal_event(
        self,
        visitor: dict[str, Any],
        event_type: str,
        severity: str,
        reason: str,
        metadata: dict[str, Any],
    ) -> None:
        """
        Admin Signal Event for the requested operation.
        
        Args:
            visitor: Visitor record involved in the operation.
            event_type: Event type filter or value used by the operation.
            severity: Severity filter or value used by the operation.
            reason: The reason value used by this operation.
            metadata: Additional metadata stored with the record or event.
        
        Returns:
            None.
        """
        await self.fraud_event_service.create_event(
            visitor_id=visitor["_id"],
            event_type=event_type,
            severity=severity,
            action=reason,
            allowed=True,
            reason=reason,
            risk_score=int(visitor.get("risk_score", 0)),
            risk_level=str(visitor.get("risk_level", "LOW")),
            fingerprint_hash=visitor.get("primary_fingerprint_hash"),
            local_storage_id=_last(visitor.get("local_storage_ids", [])),
            session_id=_last(visitor.get("session_ids", [])),
            cookie_id=visitor.get("cookie_id"),
            ip_address=_last(visitor.get("ip_addresses", [])),
            user_agent=_last(visitor.get("user_agents", [])),
            metadata=metadata,
        )


def calculate_risk_level(score: int) -> str:
    """
    Calculate Risk Level for the requested operation.
    
    Args:
        score: The score value used by this operation.
    
    Returns:
        Operation result represented as `str`.
    """
    if score <= 29:
        return RiskLevel.LOW.value
    if score <= 59:
        return RiskLevel.MEDIUM.value
    if score <= 79:
        return RiskLevel.HIGH.value
    return RiskLevel.CRITICAL.value


def _severity_for_level(level: str) -> str:
    """
    Severity For Level for the requested operation.
    
    Args:
        level: The level value used by this operation.
    
    Returns:
        Operation result represented as `str`.
    """
    if level == RiskLevel.CRITICAL.value:
        return FraudSeverity.CRITICAL.value
    if level == RiskLevel.HIGH.value:
        return FraudSeverity.HIGH.value
    if level == RiskLevel.MEDIUM.value:
        return FraudSeverity.MEDIUM.value
    return FraudSeverity.LOW.value


def _automation_signals(
    visitor: dict[str, Any],
    payload: Any | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Automation Signals for the requested operation.
    
    Args:
        visitor: Visitor record involved in the operation.
        payload: Validated request payload for this operation.
        context: Additional contextual data that influences the operation.
    
    Returns:
        Operation result represented as `dict[str, Any]`.
    """
    signals = dict(visitor.get("automation_signals", {}))
    payload_signals = getattr(payload, "automation_signals", None)
    if payload_signals:
        if hasattr(payload_signals, "model_dump"):
            signals.update(payload_signals.model_dump())
        elif isinstance(payload_signals, dict):
            signals.update(payload_signals)
    signals.update(context.get("automation_signals", {}))
    return signals


def _headless_user_agent(user_agent: str) -> bool:
    """
    Headless User Agent for the requested operation.
    
    Args:
        user_agent: User-Agent string supplied by the client.
    
    Returns:
        Operation result represented as `bool`.
    """
    value = user_agent.lower()
    return "headless" in value or "phantomjs" in value or "selenium" in value


def _zero_plugins_in_browser(user_agent: str, automation_signals: dict[str, Any]) -> bool:
    """
    Zero Plugins In Browser for the requested operation.
    
    Args:
        user_agent: User-Agent string supplied by the client.
        automation_signals: The automation signals value used by this operation.
    
    Returns:
        Operation result represented as `bool`.
    """
    if automation_signals.get("plugins_count") != 0:
        return False
    value = user_agent.lower()
    return "mozilla" in value and ("chrome" in value or "safari" in value or "firefox" in value)


def _count_recent_unique(observations: list[dict[str, Any]], since: Any) -> int:
    """
    Count Recent Unique for the requested operation.
    
    Args:
        observations: The observations value used by this operation.
        since: The since value used by this operation.
    
    Returns:
        Operation result represented as `int`.
    """
    values = set()
    for observation in observations:
        created_at = _aware(observation.get("created_at"))
        if created_at is not None and created_at >= since and observation.get("value"):
            values.add(observation["value"])
    return len(values)


def _aware(value: Any) -> datetime | None:
    """
    Aware for the requested operation.
    
    Args:
        value: Value processed by the helper.
    
    Returns:
        Operation result represented as `datetime | None`.
    """
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _unique(values: list[Any]) -> list[Any]:
    """
    Unique for the requested operation.
    
    Args:
        values: Mapping of values processed by the helper.
    
    Returns:
        Operation result represented as `list[Any]`.
    """
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _last(values: list[Any]) -> Any:
    """
    Last for the requested operation.
    
    Args:
        values: Mapping of values processed by the helper.
    
    Returns:
        Operation result represented as `Any`.
    """
    return values[-1] if values else None


def _public_ip_intel(record: dict[str, Any]) -> dict[str, Any]:
    """
    Public Ip Intel for the requested operation.
    
    Args:
        record: The record value used by this operation.
    
    Returns:
        Operation result represented as `dict[str, Any]`.
    """
    return {
        "is_vpn": bool(record.get("is_vpn", False)),
        "is_proxy": bool(record.get("is_proxy", False)),
        "is_tor": bool(record.get("is_tor", False)),
        "is_datacenter": bool(record.get("is_datacenter", False)),
        "is_known_abuser": bool(record.get("is_known_abuser", False)),
        "risk_score": int(record.get("risk_score", 0)),
        "provider": record.get("provider"),
    }
