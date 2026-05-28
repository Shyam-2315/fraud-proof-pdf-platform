import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.fraud_event import FRAUD_EVENTS_COLLECTION

logger = logging.getLogger(__name__)


class FraudEventRepository:
    """Persist and query structured fraud event documents."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection storing fraud events.

        Returns:
            Motor collection for fraud-event documents.
        """
        return get_database()[FRAUD_EVENTS_COLLECTION]

    async def create(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a fraud event document.

        Args:
            event_data: Fraud event payload to persist.

        Returns:
            Inserted fraud event document.
        """
        await self.get_collection().insert_one(event_data)
        return event_data

    async def list_events(
        self,
        limit: int = 50,
        severity: str | None = None,
        event_type: str | None = None,
        visitor_id: str | None = None,
        allowed: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return fraud events filtered by optional severity, type, visitor, and outcome.

        Args:
            limit: Maximum number of fraud events to return.
            severity: Optional fraud severity filter.
            event_type: Optional event type filter.
            visitor_id: Optional visitor filter.
            allowed: Optional allow or block outcome filter.

        Returns:
            Matching fraud event documents ordered by creation time.
        """
        filter_query = _remove_none(
            {
                "severity": severity,
                "event_type": event_type,
                "visitor_id": visitor_id,
                "allowed": allowed,
            }
        )
        cursor = (
            self.get_collection()
            .find(filter_query)
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_events(self, filter_query: dict[str, Any] | None = None) -> int:
        """
        Count fraud events matching an optional filter.

        Args:
            filter_query: Optional MongoDB filter query.

        Returns:
            Number of matching fraud event documents.
        """
        return await self.get_collection().count_documents(filter_query or {})

    async def list_by_visitor_id(
        self,
        visitor_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return recent fraud events for a visitor.

        Args:
            visitor_id: Visitor whose events should be listed.
            limit: Maximum number of events to return.

        Returns:
            Recent fraud event documents for the visitor.
        """
        cursor = (
            self.get_collection()
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


async def ensure_fraud_event_indexes() -> None:
    """Create MongoDB indexes required for fraud-event queries."""
    collection = FraudEventRepository().get_collection()
    await collection.create_index(
        [("visitor_id", ASCENDING)],
        name="idx_fraud_events_visitor_id",
    )
    await collection.create_index(
        [("event_type", ASCENDING)],
        name="idx_fraud_events_event_type",
    )
    await collection.create_index(
        [("severity", ASCENDING)],
        name="idx_fraud_events_severity",
    )
    await collection.create_index(
        [("allowed", ASCENDING)],
        name="idx_fraud_events_allowed",
    )
    await collection.create_index(
        [("created_at", DESCENDING)],
        name="idx_fraud_events_created_at",
    )
    logger.info("Ensured fraud event collection indexes")


def _remove_none(values: dict[str, Any]) -> dict[str, Any]:
    """
    Drop keys whose values are ``None`` before building a MongoDB filter.

    Args:
        values: Dictionary potentially containing ``None`` values.

    Returns:
        Dictionary containing only non-``None`` values.
    """
    return {key: value for key, value in values.items() if value is not None}
