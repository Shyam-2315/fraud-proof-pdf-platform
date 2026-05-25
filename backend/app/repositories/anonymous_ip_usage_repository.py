import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.anonymous_ip_usage import ANONYMOUS_IP_USAGE_COLLECTION

logger = logging.getLogger(__name__)


class AnonymousIPUsageRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[ANONYMOUS_IP_USAGE_COLLECTION]

    async def create_usage_event(
        self,
        usage_data: dict[str, Any],
    ) -> dict[str, Any]:
        await self.get_collection().insert_one(usage_data)
        return usage_data

    async def count_usage_in_window(
        self,
        ip_address: str,
        window_start: datetime,
    ) -> int:
        if not ip_address:
            return 0
        pipeline = [
            {
                "$match": {
                    "ip_address": ip_address,
                    "window_start": {"$gte": window_start},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$anonymous_pdf_count"},
                }
            },
        ]
        rows = await self.get_collection().aggregate(pipeline).to_list(length=1)
        if not rows:
            return 0
        return int(rows[0].get("total", 0))


async def ensure_anonymous_ip_usage_indexes() -> None:
    collection = AnonymousIPUsageRepository().get_collection()
    await collection.create_index(
        [("ip_address", ASCENDING), ("window_start", DESCENDING)],
        name="idx_anon_ip_usage_ip_window",
    )
    await collection.create_index(
        [("visitor_id", ASCENDING), ("window_start", DESCENDING)],
        name="idx_anon_ip_usage_visitor_window",
    )
    logger.info("Ensured anonymous IP usage collection indexes")
