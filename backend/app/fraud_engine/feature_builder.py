from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request

from app.fraud_engine.behavior_analyzer import BehaviorAnalyzer
from app.fraud_engine.schemas import FEATURE_COLUMNS
from app.models.fraud_event import FraudEventType
from app.repositories.fraud_engine_repository import FraudEngineRepository
from app.repositories.fraud_event_repository import FraudEventRepository
from app.repositories.identity_repository import IdentityLinkRepository
from app.repositories.risk_repository import IPIntelligenceRepository
from app.repositories.user_repository import UserRepository
from app.repositories.visitor_repository import VisitorRepository
from app.services.behavior_service import content_hash as make_content_hash
from app.services.ip_intelligence_service import IPIntelligenceService
from app.services.rate_limit_service import client_ip
from app.utils.security import generate_uuid, utc_now


class FeatureBuilder:
    def __init__(
        self,
        repository: FraudEngineRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
        fraud_event_repository: FraudEventRepository | None = None,
        identity_link_repository: IdentityLinkRepository | None = None,
        ip_repository: IPIntelligenceRepository | None = None,
        user_repository: UserRepository | None = None,
        behavior_analyzer: BehaviorAnalyzer | None = None,
        ip_intelligence_service: IPIntelligenceService | None = None,
    ) -> None:
        self.repository = repository or FraudEngineRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.fraud_event_repository = fraud_event_repository or FraudEventRepository()
        self.identity_link_repository = identity_link_repository or IdentityLinkRepository()
        self.ip_repository = ip_repository or IPIntelligenceRepository()
        self.user_repository = user_repository or UserRepository()
        self.behavior_analyzer = behavior_analyzer or BehaviorAnalyzer()
        self.ip_intelligence_service = ip_intelligence_service or IPIntelligenceService()

    async def build(
        self,
        visitor: dict[str, Any] | None,
        request: Request | None,
        action_type: str,
        user: dict[str, Any] | None = None,
        payload: Any | None = None,
        context: dict[str, Any] | None = None,
        store_snapshot: bool = True,
    ) -> dict[str, Any]:
        context = context or {}
        now = utc_now()
        visitor = visitor or {}
        visitor_id = visitor.get("_id") or visitor.get("visitor_id")
        ip_address = client_ip(request) if request is not None else _last(visitor.get("ip_addresses", []))
        headers = dict(request.headers) if request is not None else {}
        user_agent = headers.get("user-agent", _last(visitor.get("user_agents", [])) or "")
        payload_content = getattr(payload, "content", None)
        payload_hash = make_content_hash(payload_content) if payload_content else None
        behavior = (
            await self.behavior_analyzer.analyze(visitor_id, payload_hash)
            if visitor_id
            else {
                "time_to_first_generate_seconds": 999999.0,
                "avg_time_between_generations": 999999.0,
                "same_content_repeated_count": 0,
                "api_only_usage_pattern": 1,
                "page_views_before_generate": 0,
                "generate_clicks_before_success": 0,
                "recent_generate_clicks_30s": 0,
            }
        )

        cookie_ids = _unique(visitor.get("cookie_ids", []) + [visitor.get("cookie_id")])
        session_observations = visitor.get("session_observations", [])
        ip_observations = visitor.get("ip_observations", [])
        sessions_last_10_min = _count_recent_unique(session_observations, now - timedelta(minutes=10))
        ips_last_30_min = _count_recent_unique(ip_observations, now - timedelta(minutes=30))
        blocked_attempts = (
            await self.fraud_event_repository.count_events(
                {"visitor_id": visitor_id, "event_type": FraudEventType.PDF_GENERATION_BLOCKED.value}
            )
            if visitor_id
            else 0
        )
        pdf_attempts_last_10_min = (
            await self.fraud_event_repository.count_events(
                {
                    "visitor_id": visitor_id,
                    "event_type": {"$in": [FraudEventType.FRAUD_DECISION_RECORDED.value, FraudEventType.PDF_GENERATION_ALLOWED.value, FraudEventType.PDF_GENERATION_BLOCKED.value]},
                    "created_at": {"$gte": now - timedelta(minutes=10)},
                }
            )
            if visitor_id
            else 0
        )
        identity_links = (
            await self.identity_link_repository.list_by_visitor_id(visitor_id)
            if visitor_id
            else []
        )
        identity_confidence_max = max(
            [int(link.get("confidence", 0)) for link in identity_links],
            default=0,
        )
        ip_intel = await self.ip_intelligence_service.check_ip(ip_address)
        device_profile_hash = _last(visitor.get("device_profile_hashes", []))
        accounts_same_device = await self.user_repository.count_recent_by_device(
            fingerprint_hash=visitor.get("primary_fingerprint_hash"),
            device_profile_hash=device_profile_hash,
            hours=24,
        )
        accounts_same_ip = await self.user_repository.count_recent_by_ip(ip_address, hours=24)
        many_visitors_same_ip = await self.visitor_repository.count_by_ip(ip_address)
        automation_signals = dict(visitor.get("automation_signals", {}))
        automation_signals.update(context.get("automation_signals", {}))

        first_seen = _aware(visitor.get("created_at"))
        fallback_time_to_first = 999999.0
        if first_seen is not None and action_type.startswith("PDF_GENERATE"):
            fallback_time_to_first = max((now - first_seen).total_seconds(), 0.0)
        time_to_first = min(
            float(behavior.get("time_to_first_generate_seconds", 999999.0)),
            fallback_time_to_first,
        )

        features = {
            "num_cookie_ids": len(cookie_ids),
            "num_local_storage_ids": len(visitor.get("local_storage_ids", [])),
            "num_session_ids": len(visitor.get("session_ids", [])),
            "num_fingerprint_hashes": len(visitor.get("fingerprint_hashes", [])),
            "num_device_profile_hashes": len(visitor.get("device_profile_hashes", [])),
            "num_canvas_hashes": len(visitor.get("canvas_hashes", [])),
            "num_webgl_hashes": len(visitor.get("webgl_hashes", [])),
            "num_ip_addresses": len(visitor.get("ip_addresses", [])),
            "num_user_agents": len(visitor.get("user_agents", [])),
            "ip_change_count": max(len(visitor.get("ip_addresses", [])) - 1, 0),
            "sessions_last_10_min": sessions_last_10_min,
            "ips_last_30_min": ips_last_30_min,
            "pdf_attempts_last_10_min": pdf_attempts_last_10_min,
            "blocked_attempts": blocked_attempts,
            "repeated_blocked_attempts": max(blocked_attempts - 1, 0),
            "time_to_first_generate_seconds": time_to_first,
            "avg_time_between_generations": float(behavior.get("avg_time_between_generations", 999999.0)),
            "same_content_repeated_count": int(behavior.get("same_content_repeated_count", 0)),
            "api_only_usage_pattern": int(behavior.get("api_only_usage_pattern", 0)) if action_type.startswith("PDF_GENERATE") else 0,
            "page_views_before_generate": int(behavior.get("page_views_before_generate", 0)),
            "generate_clicks_before_success": int(behavior.get("generate_clicks_before_success", 0)),
            "has_vpn_ip": int(bool(ip_intel.get("is_vpn", False))),
            "has_proxy_ip": int(bool(ip_intel.get("is_proxy", False))),
            "has_datacenter_ip": int(bool(ip_intel.get("is_datacenter", False))),
            "has_tor_ip": int(bool(ip_intel.get("is_tor", False))),
            "risky_ip_score": int(ip_intel.get("risk_score", 0)),
            "webdriver_detected": int(bool(automation_signals.get("webdriver", False))),
            "plugins_count": int(automation_signals.get("plugins_count") or 0),
            "headless_suspected": int(_headless_user_agent(user_agent) or bool(automation_signals.get("headless", False))),
            "missing_browser_headers": int(_missing_browser_headers(headers)),
            "cookie_missing_after_seen": int(bool(context.get("cookie_missing_after_seen", False))),
            "same_fingerprint_multiple_cookies": int(len(cookie_ids) > 1 and bool(visitor.get("primary_fingerprint_hash"))),
            "accounts_same_device": accounts_same_device,
            "accounts_same_ip": accounts_same_ip,
            "account_created_after_free_limit": int(bool(context.get("account_created_after_free_limit", False))),
            "identity_link_confidence_max": identity_confidence_max,
            "many_visitors_same_ip": many_visitors_same_ip,
            "cleared_cookie_same_fingerprint": int(bool(context.get("cleared_cookie_same_fingerprint", False))),
            "same_ip_only": int(_same_ip_only(visitor, identity_confidence_max)),
        }
        for column in FEATURE_COLUMNS:
            features.setdefault(column, 0)

        if store_snapshot and visitor_id:
            snapshot_id = generate_uuid()
            await self.repository.create_feature_snapshot(
                {
                    "_id": snapshot_id,
                    "id": snapshot_id,
                    "visitor_id": visitor_id,
                    "user_id": user.get("_id") if user else None,
                    "action_type": action_type,
                    "features": features,
                    "created_at": now,
                }
            )
        return features


def _unique(values: list[Any]) -> list[Any]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _last(values: list[Any]) -> Any:
    return values[-1] if values else None


def _aware(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _count_recent_unique(observations: list[dict[str, Any]], since: datetime) -> int:
    values = set()
    for observation in observations:
        created_at = _aware(observation.get("created_at"))
        if created_at is not None and created_at >= since and observation.get("value"):
            values.add(observation["value"])
    return len(values)


def _headless_user_agent(user_agent: str) -> bool:
    value = user_agent.lower()
    return "headless" in value or "phantomjs" in value or "selenium" in value


def _missing_browser_headers(headers: dict[str, str]) -> bool:
    if not headers:
        return True
    normalized = {key.lower(): value for key, value in headers.items()}
    user_agent = normalized.get("user-agent", "").lower()
    if "mozilla" not in user_agent:
        return True
    return not normalized.get("accept") or not normalized.get("accept-language")


def _same_ip_only(visitor: dict[str, Any], confidence: int) -> bool:
    return (
        len(visitor.get("ip_addresses", [])) > 0
        and len(visitor.get("fingerprint_hashes", [])) <= 1
        and len(visitor.get("device_profile_hashes", [])) <= 1
        and len(visitor.get("local_storage_ids", [])) <= 1
        and confidence < 50
    )
