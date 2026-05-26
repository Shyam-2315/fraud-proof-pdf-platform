import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.behavior import BEHAVIOR_EVENTS_COLLECTION

logger = logging.getLogger(__name__)


class BehaviorEventRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[BEHAVIOR_EVENTS_COLLECTION]

    async def create(self, event: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(event)
        return event

    async def list_by_visitor_id(
        self,
        visitor_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection()
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_by_visitor(
        self,
        visitor_id: str,
        event_type: str | None = None,
        since: datetime | None = None,
    ) -> int:
        query: dict[str, Any] = {"visitor_id": visitor_id}
        if event_type is not None:
            query["event_type"] = event_type
        if since is not None:
            query["created_at"] = {"$gte": since}
        return await self.get_collection().count_documents(query)

    async def first_event(self, visitor_id: str) -> dict[str, Any] | None:
        return await self.get_collection().find_one(
            {"visitor_id": visitor_id},
            sort=[("created_at", ASCENDING)],
        )

    async def count_same_content(
        self,
        visitor_id: str,
        content_hash: str | None,
        since: datetime | None = None,
    ) -> int:
        if not content_hash:
            return 0
        query: dict[str, Any] = {
            "visitor_id": visitor_id,
            "metadata.content_hash": content_hash,
        }
        if since is not None:
            query["created_at"] = {"$gte": since}
        return await self.get_collection().count_documents(query)


async def ensure_behavior_indexes() -> None:
    collection = BehaviorEventRepository().get_collection()
    await collection.create_index(
        [("visitor_id", ASCENDING)],
        name="idx_behavior_events_visitor_id",
    )
    await collection.create_index(
        [("user_id", ASCENDING)],
        name="idx_behavior_events_user_id",
        sparse=True,
    )
    await collection.create_index(
        [("event_type", ASCENDING)],
        name="idx_behavior_events_event_type",
    )
    await collection.create_index(
        [("created_at", DESCENDING)],
        name="idx_behavior_events_created_at",
    )
    await collection.create_index(
        [("visitor_id", ASCENDING), ("created_at", DESCENDING)],
        name="idx_behavior_events_visitor_created_at",
    )
    await collection.create_index(
        [("metadata.content_hash", ASCENDING)],
        name="idx_behavior_events_content_hash",
        sparse=True,
    )
    logger.info("Ensured behavior event collection indexes")
