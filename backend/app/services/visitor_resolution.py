from typing import Any

from fastapi import Request

from app.core.auth import get_current_user_optional
from app.core.public_config import get_visitor_cookie
from app.repositories.visitor_repository import VisitorRepository
from app.utils.ip_utils import get_client_ip_details
from app.utils.security import normalize_ip, safe_append_unique, utc_now


class VisitorResolutionService:
    def __init__(
        self,
        repository: VisitorRepository | None = None,
    ) -> None:
        self.repository = repository or VisitorRepository()

    async def resolve(self, request: Request) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        current_user = await get_current_user_optional(request)
        if current_user is not None:
            return None, self._request_context(request)

        request_context = self._request_context(request)
        lookup_order = [
            ("cookie", get_visitor_cookie(request.cookies), self.repository.find_by_cookie_id),
            ("anon_id", request.headers.get("X-Anon-Id"), self.repository.find_by_cookie_id),
            ("visitor_id", request.headers.get("X-Visitor-Id"), self.repository.find_by_local_storage_id),
            ("fingerprint_hash", request.headers.get("X-Device-Fingerprint"), self.repository.find_by_fingerprint_hash),
            ("session_id", request.headers.get("X-Session-Id"), self.repository.find_by_session_id),
        ]

        for source, value, finder in lookup_order:
            visitor = await finder(value)
            if visitor is not None:
                refreshed = await self._refresh_seen_signals(
                    visitor=visitor,
                    request_context=request_context,
                    source=source,
                )
                return refreshed, request_context

        visitor = await self._find_final_fallback(request_context)
        if visitor is None:
            return None, request_context
        refreshed = await self._refresh_seen_signals(
            visitor=visitor,
            request_context=request_context,
            source="strong_fallback",
        )
        return refreshed, request_context

    async def _find_final_fallback(
        self,
        request_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        fingerprint_hash = request_context["fingerprint_hash"]
        ip_address = request_context["ip_address"]
        user_agent = request_context["user_agent"]

        if fingerprint_hash and ip_address and user_agent:
            visitor = await self.repository.find_by_fingerprint_hash(fingerprint_hash)
            if visitor is not None and ip_address in visitor.get("ip_addresses", []):
                return visitor

        device_profile_hash = request_context.get("device_profile_hash")
        if device_profile_hash and ip_address and user_agent:
            visitor = await self.repository.find_by_device_profile_hash(device_profile_hash)
            if visitor is not None and ip_address in visitor.get("ip_addresses", []):
                return visitor

        return None

    async def _refresh_seen_signals(
        self,
        *,
        visitor: dict[str, Any],
        request_context: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        now = utc_now()
        ip_address = request_context["ip_address"]
        session_id = request_context["session_id"]
        anon_id = request_context["anon_id"]
        visitor_id_header = request_context["visitor_id_header"]
        fingerprint_hash = request_context["fingerprint_hash"]
        user_agent = request_context["user_agent"]

        current_ips = list(visitor.get("ip_addresses", []))
        ip_change_history = list(visitor.get("ip_change_history", []))
        if ip_address and current_ips and ip_address not in current_ips:
            ip_change_history = safe_append_unique(
                ip_change_history,
                {
                    "previous_ip": current_ips[-1],
                    "current_ip": ip_address,
                    "changed_at": now,
                    "visitor_id": visitor.get("_id"),
                    "fingerprint_hash": fingerprint_hash,
                    "user_agent": user_agent,
                    "event_type": "DYNAMIC_IP_CHANGE",
                },
                max_items=50,
            )

        update_data = {
            "cookie_ids": safe_append_unique(visitor.get("cookie_ids", []), anon_id),
            "local_storage_ids": safe_append_unique(
                visitor.get("local_storage_ids", []),
                visitor_id_header or anon_id,
            ),
            "session_ids": safe_append_unique(visitor.get("session_ids", []), session_id),
            "fingerprint_hashes": safe_append_unique(
                visitor.get("fingerprint_hashes", []),
                fingerprint_hash,
            ),
            "ip_addresses": safe_append_unique(current_ips, ip_address),
            "user_agents": safe_append_unique(visitor.get("user_agents", []), user_agent),
            "ip_change_history": ip_change_history,
            "last_resolution_source": source,
            "last_seen_at": now,
        }
        updated = await self.repository.update_visitor(visitor["_id"], update_data)
        return updated or {**visitor, **update_data}

    def _request_context(self, request: Request) -> dict[str, Any]:
        ip_details = get_client_ip_details(request)
        return {
            "anon_id": get_visitor_cookie(request.cookies) or request.headers.get("X-Anon-Id"),
            "visitor_id_header": request.headers.get("X-Visitor-Id"),
            "session_id": request.headers.get("X-Session-Id"),
            "fingerprint_hash": request.headers.get("X-Device-Fingerprint"),
            "device_profile_hash": request.headers.get("X-Device-Profile-Hash"),
            "user_agent": request.headers.get("user-agent", ""),
            "ip_address": normalize_ip(ip_details["resolved_client_ip"]),
            "ip_details": ip_details,
        }
