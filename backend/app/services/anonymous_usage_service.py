from datetime import timedelta
from typing import Any

from app.config import get_settings
from app.repositories.anonymous_ip_usage_repository import AnonymousIPUsageRepository
from app.utils.security import generate_uuid, normalize_ip, utc_now


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
        return utc_now() - timedelta(hours=int(self.settings.ANON_IP_USAGE_WINDOW_HOURS))

    async def get_ip_usage_count(self, ip_address: str | None) -> int:
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return 0
        return await self.repository.count_usage_in_window(
            ip_address=normalized_ip,
            window_start=self._window_start(),
        )

    async def record_anonymous_pdf_usage(
        self,
        ip_address: str | None,
        visitor_id: str,
    ) -> None:
        normalized_ip = normalize_ip(ip_address)
        if not normalized_ip or normalized_ip == "unknown":
            return
        now = utc_now()
        await self.repository.create_usage_event(
            {
                "_id": generate_uuid(),
                "ip_address": normalized_ip,
                "window_start": now,
                "anonymous_pdf_count": 1,
                "visitor_id": visitor_id,
                "visitor_ids": [visitor_id],
                "first_seen_at": now,
                "last_seen_at": now,
            }
        )

    async def build_shared_usage_summary(
        self,
        *,
        visitor: dict[str, Any] | None,
        ip_address: str | None,
    ) -> dict[str, int]:
        visitor_usage_count = int((visitor or {}).get("free_usage_count", 0))
        free_usage_limit = self.free_usage_limit()
        if not self.shared_ip_quota_enabled():
            shared_usage_count = visitor_usage_count
        else:
            ip_usage_count = await self.get_ip_usage_count(ip_address)
            shared_usage_count = max(visitor_usage_count, ip_usage_count)
        return {
            "free_usage_count": shared_usage_count,
            "free_usage_limit": free_usage_limit,
            "remaining_free_uses": max(free_usage_limit - shared_usage_count, 0),
        }
