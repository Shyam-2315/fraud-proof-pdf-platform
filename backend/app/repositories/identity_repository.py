import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.identity import VISITOR_IDENTITY_LINKS_COLLECTION
from app.utils.security import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class IdentityLinkRepository:
    """Persist and query visitor identity-link records."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection storing identity links.

        Returns:
            Motor collection for identity-link documents.
        """
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
        """
        Create an identity link between two visitors when one does not already exist.

        Args:
            source_visitor_id: Visitor that initiated the relationship.
            target_visitor_id: Visitor matched to the source visitor.
            link_type: Link type describing the relationship strength.
            confidence: Confidence score for the relationship.
            reason: Human-readable explanation of the match.
            matched_signals: Optional signal payload supporting the link.

        Returns:
            Existing or newly inserted identity-link document.
        """
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
        """
        Return identity links where the visitor appears as source or target.

        Args:
            visitor_id: Visitor whose links should be listed.
            limit: Maximum number of links to return.

        Returns:
            Recent identity-link documents associated with the visitor.
        """
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
        """
        Count high-confidence identity links used as duplicate signals.

        Returns:
            Number of identity links with confidence greater than or equal to 80.
        """
        return await self.get_collection().count_documents({"confidence": {"$gte": 80}})

    async def count_links(self, filter_query: dict[str, Any] | None = None) -> int:
        """
        Count identity links matching an optional filter.

        Args:
            filter_query: Optional MongoDB filter query.

        Returns:
            Number of matching identity-link documents.
        """
        return await self.get_collection().count_documents(filter_query or {})


async def ensure_identity_link_indexes() -> None:
    """Create MongoDB indexes required for identity-link queries."""
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
