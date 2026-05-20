import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.identity import VISITOR_IDENTITY_LINKS_COLLECTION
from app.utils.security import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class IdentityLinkRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[VISITOR_IDENTITY_LINKS_COLLECTION]

    async def create_link(
        self,
        source_visitor_id: str,
        target_visitor_id: str,
        link_type: str,
        confidence: int,
        reason: str,
        matched_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = await self.get_collection().find_one(
            {
                "source_visitor_id": source_visitor_id,
                "target_visitor_id": target_visitor_id,
                "link_type": link_type,
            }
        )
        if existing is not None:
            return existing

        link_id = generate_uuid()
        link = {
            "_id": link_id,
            "id": link_id,
            "source_visitor_id": source_visitor_id,
            "target_visitor_id": target_visitor_id,
            "link_type": link_type,
            "confidence": int(confidence),
            "reason": reason,
            "matched_signals": matched_signals or {},
            "created_at": utc_now(),
        }
        await self.get_collection().insert_one(link)
        return link

    async def list_by_visitor_id(
        self,
        visitor_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection()
            .find(
                {
                    "$or": [
                        {"source_visitor_id": visitor_id},
                        {"target_visitor_id": visitor_id},
                    ]
                }
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_duplicate_links(self) -> int:
        return await self.get_collection().count_documents({"confidence": {"$gte": 80}})

    async def count_links(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.get_collection().count_documents(filter_query or {})


async def ensure_identity_link_indexes() -> None:
    collection = IdentityLinkRepository().get_collection()
    await collection.create_index(
        [("source_visitor_id", ASCENDING)],
        name="idx_identity_links_source_visitor_id",
    )
    await collection.create_index(
        [("target_visitor_id", ASCENDING)],
        name="idx_identity_links_target_visitor_id",
    )
    await collection.create_index(
        [("link_type", ASCENDING)],
        name="idx_identity_links_link_type",
    )
    await collection.create_index(
        [("confidence", DESCENDING)],
        name="idx_identity_links_confidence",
    )
    await collection.create_index(
        [("created_at", DESCENDING)],
        name="idx_identity_links_created_at",
    )
    logger.info("Ensured identity link collection indexes")
