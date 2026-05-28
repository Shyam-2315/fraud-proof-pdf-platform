import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.behavior import BEHAVIOR_EVENTS_COLLECTION

logger = logging.getLogger(__name__)


class BehaviorEventRepository:
    """Persist and query visitor behavior telemetry events."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection storing behavior events.

        Returns:
            Motor collection for behavior-event documents.
        """
        return get_database()[BEHAVIOR_EVENTS_COLLECTION]

    async def create(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a behavior event document.

        Args:
            event: Behavior event payload to persist.

        Returns:
            Inserted behavior event document.
        """
        await self.get_collection().insert_one(event)
        return event

    async def list_by_visitor_id(
        self,
        visitor_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return recent behavior events for a visitor.

        Args:
            visitor_id: Visitor whose events should be listed.
            limit: Maximum number of events to return.

        Returns:
            Recent behavior-event documents for the visitor.
        """
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
        """
        Count behavior events for a visitor with optional filters.

        Args:
            visitor_id: Visitor whose events should be counted.
            event_type: Optional event-type filter.
            since: Optional lower timestamp bound.

        Returns:
            Number of matching behavior events.
        """
        query: dict[str, Any] = {"visitor_id": visitor_id}
        if event_type is not None:
            query["event_type"] = event_type
        if since is not None:
            query["created_at"] = {"$gte": since}
        return await self.get_collection().count_documents(query)

    async def first_event(self, visitor_id: str) -> dict[str, Any] | None:
        """
        Return the earliest behavior event recorded for a visitor.

        Args:
            visitor_id: Visitor whose first event should be loaded.

        Returns:
            Earliest behavior event document, or ``None`` when no events exist.
        """
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
        """
        Count repeated behavior events for the same content hash.

        Args:
            visitor_id: Visitor whose events should be inspected.
            content_hash: Content hash used to group repeated content.
            since: Optional lower timestamp bound.

        Returns:
            Number of matching content-hash events.
        """
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
    """Create MongoDB indexes required for behavior-event queries."""
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
