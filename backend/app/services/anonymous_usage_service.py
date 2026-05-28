import logging
from datetime import timedelta
from typing import Any

from fastapi import Request

from app.config import get_settings
from app.core.public_config import LOGIN_REQUIRED_MESSAGE
from app.repositories.anonymous_ip_usage_repository import AnonymousIPUsageRepository
from app.utils.request_utils import get_normalized_client_ip
from app.utils.security import normalize_ip, utc_now

logger = logging.getLogger(__name__)
_GENERIC_BLOCK_MESSAGE = "We could not process this request right now. Please try again later."
_LIMIT_BLOCK_REASON = "FREE_LIMIT_REACHED"


class AnonymousUsageService:
    """
    Service that coordinates domain workflows and business rules.
    """
    def __init__(
        self,
        repository: AnonymousIPUsageRepository | None = None,
    ) -> None:
        """
        Initialize the service with optional collaborators and runtime dependencies.
        
        Args:
            repository: The repository value used by this operation.
        
        Returns:
            None.
        """
        self.settings = get_settings()
        self.repository = repository or AnonymousIPUsageRepository()

    def shared_ip_quota_enabled(self) -> bool:
        """
        Shared Ip Quota Enabled for the requested operation.
        
        Returns:
            Operation result represented as `bool`.
        """
        return bool(self.settings.ENABLE_SHARED_IP_ANON_QUOTA)

    def free_usage_limit(self) -> int:
        """
        Free Usage Limit for the requested operation.
        
        Returns:
            Operation result represented as `int`.
        """
        return int(self.settings.ANON_SHARED_IP_FREE_LIMIT)

    def _window_start(self):
        """
        Window Start for the requested operation.
        
        Returns:
            Operation result for the requested workflow.
        """
        return utc_now()

    def _window_end(self, start):
        """
        Window End for the requested operation.
        
        Args:
            start: The start value used by this operation.
        
        Returns:
            Operation result for the requested workflow.
        """
        return start + timedelta(hours=int(self.settings.ANON_IP_USAGE_WINDOW_HOURS))

    async def get_ip_usage_count(self, ip_address: str | None) -> int:
        """
        Return ip usage count data for the service workflow.
        
        Args:
            ip_address: IP address being analyzed or persisted.
        
        Returns:
            Matching record or value when available.
        """
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return 0
        return await self.repository.get_usage_count(ip_address=normalized_ip, now=utc_now())

    async def record_anonymous_pdf_usage(
        self,
        ip_address: str | None,
        visitor_id: str,
        anon_id: str | None = None,
        fingerprint_hash: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Record anonymous pdf usage data for the service workflow.
        
        Args:
            ip_address: IP address being analyzed or persisted.
            visitor_id: Unique visitor identifier used by the operation.
            anon_id: Unique anon identifier used by the operation.
            fingerprint_hash: Device fingerprint hash associated with the caller.
            user_agent: User-Agent string supplied by the client.
        
        Returns:
            Outcome of the requested operation.
        """
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return None
        window_start = self._window_start()
        return await self.repository.upsert_usage_window(
            ip_address=normalized_ip,
            now=window_start,
            window_start=window_start,
            window_end=self._window_end(window_start),
            visitor_id=visitor_id,
            anon_id=anon_id,
            fingerprint_hash=fingerprint_hash,
            user_agent=user_agent,
        )

    async def get_active_window(self, ip_address: str | None) -> dict[str, Any] | None:
        """
        Return active window data for the service workflow.
        
        Args:
            ip_address: IP address being analyzed or persisted.
        
        Returns:
            Matching record or value when available.
        """
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return None
        return await self.repository.find_active_window(
            ip_address=normalized_ip,
            now=utc_now(),
        )

    async def get_shared_usage_snapshot(
        self,
        *,
        visitor: dict[str, Any] | None,
        ip_address: str | None,
        active_window: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Return shared usage snapshot data for the service workflow.
        
        Args:
            visitor: Visitor record involved in the operation.
            ip_address: IP address being analyzed or persisted.
            active_window: The active window value used by this operation.
        
        Returns:
            Matching record or value when available.
        """
        visitor_usage_count = int((visitor or {}).get("free_usage_count") or 0)
        free_usage_limit = self.free_usage_limit()
        normalized_ip = normalize_ip(ip_address)
        current_window = active_window
        ip_usage_count = 0

        if self.shared_ip_quota_enabled() and normalized_ip and normalized_ip != "unknown":
            if current_window is None:
                current_window = await self.get_active_window(normalized_ip)
            ip_usage_count = int((current_window or {}).get("anonymous_pdf_count") or 0)

        shared_usage_count = (
            max(visitor_usage_count, ip_usage_count)
            if self.shared_ip_quota_enabled()
            else visitor_usage_count
        )
        return {
            "visitor_usage_count": visitor_usage_count,
            "ip_usage_count": ip_usage_count,
            "free_usage_count": shared_usage_count,
            "free_usage_limit": free_usage_limit,
            "remaining_free_uses": max(free_usage_limit - shared_usage_count, 0),
            "active_window": current_window,
        }

    async def build_shared_usage_summary(
        self,
        *,
        visitor: dict[str, Any] | None,
        ip_address: str | None,
        active_window: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """
        Build shared usage summary data for the service workflow.
        
        Args:
            visitor: Visitor record involved in the operation.
            ip_address: IP address being analyzed or persisted.
            active_window: The active window value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        snapshot = await self.get_shared_usage_snapshot(
            visitor=visitor,
            ip_address=ip_address,
            active_window=active_window,
        )
        return {
            "free_usage_count": int(snapshot["free_usage_count"]),
            "free_usage_limit": int(snapshot["free_usage_limit"]),
            "remaining_free_uses": int(snapshot["remaining_free_uses"]),
        }

    async def get_anonymous_usage_status(
        self,
        *,
        request: Request,
        visitor: dict[str, Any] | None,
        active_window: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Return anonymous usage status data for the service workflow.
        
        Args:
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
            visitor: Visitor record involved in the operation.
            active_window: The active window value used by this operation.
        
        Returns:
            Matching record or value when available.
        """
        normalized_ip = get_normalized_client_ip(request)
        snapshot = await self.get_shared_usage_snapshot(
            visitor=visitor,
            ip_address=normalized_ip,
            active_window=active_window,
        )
        visitor_usage_count = int(snapshot["visitor_usage_count"])
        ip_usage_count = int(snapshot["ip_usage_count"])
        fingerprint_hash = request.headers.get("X-Device-Fingerprint")
        device_profile_hash = request.headers.get("X-Device-Profile-Hash")
        fingerprint_usage_count = (
            visitor_usage_count
            if fingerprint_hash and fingerprint_hash in (visitor or {}).get("fingerprint_hashes", [])
            else 0
        )
        device_usage_count = (
            visitor_usage_count
            if device_profile_hash and device_profile_hash in (visitor or {}).get("device_profile_hashes", [])
            else 0
        )
        used = max(
            visitor_usage_count,
            ip_usage_count,
            device_usage_count,
            fingerprint_usage_count,
        )
        free_limit = int(snapshot["free_usage_limit"])
        remaining = max(free_limit - used, 0)
        block_state = self._block_state(visitor=visitor, remaining=remaining)
        limit_reached = block_state["limit_reached"]
        fraud_blocked = block_state["fraud_blocked"]
        visitor_blocked = block_state["visitor_blocked"]
        block_reason = block_state["block_reason"]
        is_blocked = limit_reached or fraud_blocked
        message = (
            LOGIN_REQUIRED_MESSAGE
            if limit_reached
            else _GENERIC_BLOCK_MESSAGE
            if fraud_blocked
            else None
        )

        log = (
            logger.info
            if is_blocked or visitor_blocked or ip_usage_count > 0 or used != visitor_usage_count
            else logger.debug
        )
        log(
            "Anonymous usage status visitor_id=%s ip=%s visitor_usage=%s ip_usage=%s device_usage=%s fingerprint_usage=%s used=%s remaining=%s limit_reached=%s fraud_blocked=%s visitor_blocked=%s block_reason=%s is_blocked=%s",
            (visitor or {}).get("_id"),
            normalized_ip,
            visitor_usage_count,
            ip_usage_count,
            device_usage_count,
            fingerprint_usage_count,
            used,
            remaining,
            limit_reached,
            fraud_blocked,
            visitor_blocked,
            block_reason,
            is_blocked,
        )

        return {
            "used": used,
            "remaining": remaining,
            "free_limit": free_limit,
            "free_usage_count": used,
            "free_usage_limit": free_limit,
            "remaining_free_uses": remaining,
            "visitor_usage_count": visitor_usage_count,
            "ip_usage_count": ip_usage_count,
            "device_usage_count": device_usage_count,
            "fingerprint_usage_count": fingerprint_usage_count,
            "limit_reached": limit_reached,
            "fraud_blocked": fraud_blocked,
            "visitor_blocked": visitor_blocked,
            "block_reason": block_reason,
            "is_blocked": is_blocked,
            "message": message,
            "requires_login": limit_reached,
            "active_window": snapshot.get("active_window"),
        }

    def _block_state(
        self,
        *,
        visitor: dict[str, Any] | None,
        remaining: int,
    ) -> dict[str, bool | str | None]:
        """Classify anonymous visitor blocking into limit and explicit-fraud buckets."""
        stored_block_reason = str((visitor or {}).get("block_reason") or "").strip() or None
        visitor_blocked = bool((visitor or {}).get("is_blocked", False))
        limit_reached = remaining <= 0
        # Legacy visitor records may still carry raw block flags from old free-limit logic.
        # Treat only explicit non-limit reasons as fraud/manual blocks.
        fraud_blocked = stored_block_reason not in {None, _LIMIT_BLOCK_REASON}
        block_reason = (
            _LIMIT_BLOCK_REASON
            if limit_reached
            else stored_block_reason
            if fraud_blocked
            else None
        )
        return {
            "limit_reached": limit_reached,
            "fraud_blocked": fraud_blocked,
            "visitor_blocked": visitor_blocked,
            "block_reason": block_reason,
        }
