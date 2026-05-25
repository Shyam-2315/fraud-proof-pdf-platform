from datetime import timedelta
from typing import Any

from app.config import get_settings
from app.repositories.anonymous_ip_usage_repository import AnonymousIPUsageRepository
from app.utils.security import normalize_ip, utc_now


class AnonymousUsageService:
    def __init__(
        self,
        repository: AnonymousIPUsageRepository | None = None,
    ) -> None:
        self.settings = get_settings()
        self.repository = repository or AnonymousIPUsageRepository()

    def shared_ip_quota_enabled(self) -> bool:
        return bool(self.settings.ENABLE_SHARED_IP_ANON_QUOTA)

    def free_usage_limit(self) -> int:
        return int(self.settings.ANON_SHARED_IP_FREE_LIMIT)

    def _window_start(self):
        return utc_now()

    def _window_end(self, start):
        return start + timedelta(hours=int(self.settings.ANON_IP_USAGE_WINDOW_HOURS))

    async def get_ip_usage_count(self, ip_address: str | None) -> int:
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
    ) -> None:
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return
        window_start = self._window_start()
        await self.repository.upsert_usage_window(
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
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return None
        return await self.repository.find_active_window(
            ip_address=normalized_ip,
            now=utc_now(),
        )

    async def build_shared_usage_summary(
        self,
        *,
        visitor: dict[str, Any] | None,
        ip_address: str | None,
    ) -> dict[str, int]:
        visitor_usage_count = int((visitor or {}).get("free_usage_count") or 0)
        free_usage_limit = self.free_usage_limit()
        if not self.shared_ip_quota_enabled():
            shared_usage_count = visitor_usage_count
        else:
            ip_usage_count = await self.get_ip_usage_count(ip_address) if ip_address else 0
            shared_usage_count = max(visitor_usage_count, ip_usage_count)
        return {
            "free_usage_count": shared_usage_count,
            "free_usage_limit": free_usage_limit,
            "remaining_free_uses": max(free_usage_limit - shared_usage_count, 0),
        }
