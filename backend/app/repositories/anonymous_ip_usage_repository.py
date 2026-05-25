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

    async def find_active_window(
        self,
        ip_address: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        if not ip_address:
            return None
        return await self.get_collection().find_one(
            {
                "ip_address": ip_address,
                "window_start": {"$lte": now},
                "window_end": {"$gt": now},
            }
        )

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
        active = await self.find_active_window(ip_address=ip_address, now=now)
        selector = {"_id": active["_id"]} if active is not None else {
            "ip_address": ip_address,
            "window_start": window_start,
        }
        effective_window_start = active.get("window_start", window_start) if active else window_start
        effective_window_end = active.get("window_end", window_end) if active else window_end
        return await self.get_collection().find_one_and_update(
            selector,
            {
                "$inc": {"anonymous_pdf_count": 1},
                "$set": {
                    "ip_address": ip_address,
                    "window_start": effective_window_start,
                    "window_end": effective_window_end,
                    "updated_at": now,
                    "last_seen_at": now,
                },
                "$setOnInsert": {
                    "first_seen_at": now,
                    "visitor_ids": [],
                    "anon_ids": [],
                    "fingerprint_hashes": [],
                    "user_agents": [],
                },
                "$addToSet": {
                    "visitor_ids": {"$each": [value for value in [visitor_id] if value]},
                    "anon_ids": {"$each": [value for value in [anon_id] if value]},
                    "fingerprint_hashes": {"$each": [value for value in [fingerprint_hash] if value]},
                    "user_agents": {"$each": [value for value in [user_agent] if value]},
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def get_usage_count(
        self,
        ip_address: str,
        now: datetime,
    ) -> int:
        active = await self.find_active_window(ip_address=ip_address, now=now)
        if active is None:
            return 0
        return int(active.get("anonymous_pdf_count", 0))

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
