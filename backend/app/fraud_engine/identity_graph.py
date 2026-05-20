from typing import Any

from app.models.identity import IdentityLinkType
from app.repositories.identity_repository import IdentityLinkRepository
from app.repositories.visitor_repository import VisitorRepository


class IdentityGraphService:
    def __init__(
        self,
        visitor_repository: VisitorRepository | None = None,
        identity_link_repository: IdentityLinkRepository | None = None,
    ) -> None:
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.identity_link_repository = identity_link_repository or IdentityLinkRepository()

    async def find_strong_match(
        self,
        signals: dict[str, Any],
    ) -> dict[str, Any] | None:
        candidates = await self._candidate_visitors(signals, strong_only=True)
        best: dict[str, Any] | None = None
        best_confidence = 0
        for candidate in candidates:
            confidence = self.calculate_match_confidence(candidate, signals)
            if confidence > best_confidence:
                best = candidate
                best_confidence = confidence
        return best if best is not None and best_confidence >= 80 else None

    async def find_related_match(
        self,
        signals: dict[str, Any],
    ) -> dict[str, Any] | None:
        candidates = await self._candidate_visitors(signals, strong_only=False)
        best: dict[str, Any] | None = None
        best_confidence = 0
        for candidate in candidates:
            confidence = self.calculate_match_confidence(candidate, signals)
            if confidence > best_confidence:
                best = candidate
                best_confidence = confidence
        return best if best is not None and best_confidence > 0 else None

    async def create_identity_link(
        self,
        source_visitor_id: str,
        target_visitor_id: str,
        link_type: str,
        confidence: int,
        reason: str,
        matched_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.identity_link_repository.create_link(
            source_visitor_id=source_visitor_id,
            target_visitor_id=target_visitor_id,
            link_type=link_type,
            confidence=confidence,
            reason=reason,
            matched_signals=matched_signals,
        )

    async def get_links_for_visitor(
        self,
        visitor_id: str,
    ) -> list[dict[str, Any]]:
        return await self.identity_link_repository.list_by_visitor_id(visitor_id)

    def calculate_match_confidence(
        self,
        existing_visitor: dict[str, Any],
        incoming_signals: dict[str, Any],
    ) -> int:
        return self.describe_match(existing_visitor, incoming_signals)["confidence"]

    def describe_match(
        self,
        existing_visitor: dict[str, Any],
        incoming_signals: dict[str, Any],
    ) -> dict[str, Any]:
        checks = [
            (
                "cookie_id",
                _cookie_ids(existing_visitor),
                IdentityLinkType.COOKIE_MATCH.value,
                100,
                "Same cookie ID matched an existing visitor.",
            ),
            (
                "local_storage_id",
                existing_visitor.get("local_storage_ids", []),
                IdentityLinkType.LOCAL_STORAGE_MATCH.value,
                90,
                "Same local storage ID matched an existing visitor.",
            ),
            (
                "fingerprint_hash",
                existing_visitor.get("fingerprint_hashes", []),
                IdentityLinkType.FINGERPRINT_MATCH.value,
                80,
                "Same fingerprint hash matched an existing visitor.",
            ),
            (
                "canvas_hash",
                existing_visitor.get("canvas_hashes", []),
                IdentityLinkType.CANVAS_HASH_MATCH.value,
                70,
                "Same canvas hash matched an existing visitor.",
            ),
            (
                "webgl_hash",
                existing_visitor.get("webgl_hashes", []),
                IdentityLinkType.WEBGL_HASH_MATCH.value,
                70,
                "Same WebGL hash matched an existing visitor.",
            ),
            (
                "device_profile_hash",
                existing_visitor.get("device_profile_hashes", []),
                IdentityLinkType.DEVICE_PROFILE_MATCH.value,
                70,
                "Same device profile hash matched an existing visitor.",
            ),
        ]
        for signal_name, existing_values, link_type, confidence, reason in checks:
            incoming_value = incoming_signals.get(signal_name)
            if incoming_value and incoming_value in existing_values:
                return {
                    "confidence": confidence,
                    "link_type": link_type,
                    "reason": reason,
                    "matched_signals": _matched_signals(incoming_signals, signal_name),
                }

        ip_address = incoming_signals.get("ip_address")
        user_agent = incoming_signals.get("user_agent")
        ip_matches = bool(ip_address and ip_address in existing_visitor.get("ip_addresses", []))
        user_agent_matches = bool(
            user_agent and user_agent in existing_visitor.get("user_agents", [])
        )
        if ip_matches and user_agent_matches:
            return {
                "confidence": 40,
                "link_type": IdentityLinkType.IP_USER_AGENT_MATCH.value,
                "reason": "Same IP and user-agent matched an existing visitor.",
                "matched_signals": _matched_signals(
                    incoming_signals,
                    "ip_address",
                    "user_agent",
                ),
            }
        if ip_matches:
            return {
                "confidence": 10,
                "link_type": IdentityLinkType.IP_USER_AGENT_MATCH.value,
                "reason": "Same IP matched an existing visitor.",
                "matched_signals": _matched_signals(incoming_signals, "ip_address"),
            }

        session_id = incoming_signals.get("session_id")
        if session_id and session_id in existing_visitor.get("session_ids", []):
            return {
                "confidence": 50,
                "link_type": IdentityLinkType.SESSION_PATTERN_MATCH.value,
                "reason": "Session pattern matched an existing visitor.",
                "matched_signals": _matched_signals(incoming_signals, "session_id"),
            }

        return {
            "confidence": 0,
            "link_type": IdentityLinkType.SESSION_PATTERN_MATCH.value,
            "reason": "No matching visitor signals.",
            "matched_signals": {},
        }

    async def _candidate_visitors(
        self,
        signals: dict[str, Any],
        strong_only: bool,
    ) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        cookie_id = signals.get("cookie_id")
        if cookie_id:
            filters.extend([{"cookie_id": cookie_id}, {"cookie_ids": cookie_id}])
        if signals.get("local_storage_id"):
            filters.append({"local_storage_ids": signals["local_storage_id"]})
        if signals.get("fingerprint_hash"):
            filters.append({"fingerprint_hashes": signals["fingerprint_hash"]})
        if not strong_only:
            if signals.get("canvas_hash"):
                filters.append({"canvas_hashes": signals["canvas_hash"]})
            if signals.get("webgl_hash"):
                filters.append({"webgl_hashes": signals["webgl_hash"]})
            if signals.get("device_profile_hash"):
                filters.append({"device_profile_hashes": signals["device_profile_hash"]})
            if signals.get("ip_address"):
                filters.append({"ip_addresses": signals["ip_address"]})
            if signals.get("session_id"):
                filters.append({"session_ids": signals["session_id"]})
        if not filters:
            return []

        cursor = self.visitor_repository.get_collection().find({"$or": filters}).limit(20)
        visitors = await cursor.to_list(length=20)
        unique: dict[str, dict[str, Any]] = {}
        for visitor in visitors:
            unique[str(visitor.get("_id"))] = visitor
        return list(unique.values())


def _cookie_ids(visitor: dict[str, Any]) -> list[str]:
    values = []
    if visitor.get("cookie_id"):
        values.append(visitor["cookie_id"])
    values.extend(visitor.get("cookie_ids", []))
    return [value for index, value in enumerate(values) if value and value not in values[:index]]


def _matched_signals(
    signals: dict[str, Any],
    *names: str,
) -> dict[str, Any]:
    return {name: signals.get(name) for name in names if signals.get(name)}


__all__ = ["IdentityGraphService", "IdentityLinkRepository"]
