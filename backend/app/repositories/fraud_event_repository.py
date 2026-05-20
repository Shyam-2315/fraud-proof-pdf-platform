import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.fraud_event import FRAUD_EVENTS_COLLECTION

logger = logging.getLogger(__name__)


class FraudEventRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[FRAUD_EVENTS_COLLECTION]

    async def create(self, event_data: dict[str, Any]) -> dict[str, Any]:
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
        return await self.get_collection().count_documents(filter_query or {})

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


async def ensure_fraud_event_indexes() -> None:
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
    return {key: value for key, value in values.items() if value is not None}
