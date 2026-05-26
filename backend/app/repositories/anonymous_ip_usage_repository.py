import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, ReturnDocument

from app.database import get_database
from app.models.anonymous_ip_usage import ANONYMOUS_IP_USAGE_COLLECTION

logger = logging.getLogger(__name__)


class AnonymousIPUsageRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[ANONYMOUS_IP_USAGE_COLLECTION]

    def _active_window_filter(
        self,
        ip_address: str,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "ip_address": ip_address,
            "window_start": {"$lte": now},
            "window_end": {"$gt": now},
        }

    async def find_active_window(
        self,
        ip_address: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        if not ip_address:
            return None
        active_windows = await self.find_active_windows(ip_address=ip_address, now=now)
        if not active_windows:
            return None

        visitor_ids: set[str] = set()
        anon_ids: set[str] = set()
        fingerprint_hashes: set[str] = set()
        user_agents: set[str] = set()
        for window in active_windows:
            visitor_ids.update(window.get("visitor_ids", []))
            anon_ids.update(window.get("anon_ids", []))
            fingerprint_hashes.update(window.get("fingerprint_hashes", []))
            user_agents.update(window.get("user_agents", []))

        return {
            "_id": active_windows[0]["_id"],
            "ip_address": ip_address,
            "window_start": min(window["window_start"] for window in active_windows),
            "window_end": max(window["window_end"] for window in active_windows),
            "first_seen_at": min(window.get("first_seen_at", window["window_start"]) for window in active_windows),
            "last_seen_at": max(window.get("last_seen_at", window["window_start"]) for window in active_windows),
            "updated_at": max(window.get("updated_at", window["window_start"]) for window in active_windows),
            "anonymous_pdf_count": sum(int(window.get("anonymous_pdf_count", 0)) for window in active_windows),
            "visitor_ids": sorted(visitor_ids),
            "anon_ids": sorted(anon_ids),
            "fingerprint_hashes": sorted(fingerprint_hashes),
            "user_agents": sorted(user_agents),
        }

    async def find_active_windows(
        self,
        ip_address: str,
        now: datetime,
    ) -> list[dict[str, Any]]:
        if not ip_address:
            return []
        cursor = (
            self.get_collection()
            .find(self._active_window_filter(ip_address=ip_address, now=now))
            .sort("window_start", -1)
        )
        return await cursor.to_list(length=1000)

    async def upsert_usage_window(
        self,
        *,
        ip_address: str,
        now: datetime,
        window_start: datetime,
        window_end: datetime,
        visitor_id: str | None,
        anon_id: str | None,
        fingerprint_hash: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        active_windows = await self.find_active_windows(ip_address=ip_address, now=now)
        active = active_windows[0] if active_windows else None
        selector = {"_id": active["_id"]} if active is not None else {
            "ip_address": ip_address,
            "window_start": window_start,
        }
        effective_window_start = active.get("window_start", window_start) if active else window_start
        effective_window_end = active.get("window_end", window_end) if active else window_end
        add_to_set_fields: dict[str, Any] = {}
        if visitor_id:
            add_to_set_fields["visitor_ids"] = visitor_id
        if anon_id:
            add_to_set_fields["anon_ids"] = anon_id
        if fingerprint_hash:
            add_to_set_fields["fingerprint_hashes"] = fingerprint_hash
        if user_agent:
            add_to_set_fields["user_agents"] = user_agent

        update_document: dict[str, Any] = {
            "$inc": {"anonymous_pdf_count": 1},
            "$setOnInsert": {
                "ip_address": ip_address,
                "window_start": effective_window_start,
                "window_end": effective_window_end,
                "first_seen_at": now,
            },
            "$set": {
                "last_seen_at": now,
                "updated_at": now,
            },
        }
        if add_to_set_fields:
            update_document["$addToSet"] = add_to_set_fields

        return await self.get_collection().find_one_and_update(
            selector,
            update_document,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def get_usage_count(
        self,
        ip_address: str,
        now: datetime,
    ) -> int:
        active_windows = await self.find_active_windows(ip_address=ip_address, now=now)
        if not active_windows:
            return 0
        return sum(int(window.get("anonymous_pdf_count", 0)) for window in active_windows)

    async def list_recent(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cursor = self.get_collection().find({}).sort("updated_at", -1).limit(limit)
        return await cursor.to_list(length=limit)


async def ensure_anonymous_ip_usage_indexes() -> None:
    collection = AnonymousIPUsageRepository().get_collection()
    await collection.create_index(
        [("ip_address", ASCENDING)],
        name="idx_anon_ip_usage_ip_address",
    )
    await collection.create_index(
        [("window_start", ASCENDING)],
        name="idx_anon_ip_usage_window_start",
    )
    await collection.create_index(
        [("window_end", ASCENDING)],
        name="idx_anon_ip_usage_window_end",
    )
    await collection.create_index(
        [("ip_address", ASCENDING), ("window_start", ASCENDING)],
        name="idx_anon_ip_usage_ip_window_start",
    )
    logger.info("Ensured anonymous IP usage collection indexes")
