import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.fraud import BLOCKED_ENTITIES_COLLECTION, FRAUD_EVENTS_COLLECTION

logger = logging.getLogger(__name__)


class FraudRepository:
    """
    Repository that encapsulates database access for the domain model.
    """
    def get_fraud_events_collection(self) -> AsyncIOMotorCollection:
        """
        Fetch fraud events collection data from persistence.
        
        Returns:
            Matching record or value when available.
        """
        return get_database()[FRAUD_EVENTS_COLLECTION]

    def get_blocked_entities_collection(self) -> AsyncIOMotorCollection:
        """
        Fetch blocked entities collection data from persistence.
        
        Returns:
            Matching record or value when available.
        """
        return get_database()[BLOCKED_ENTITIES_COLLECTION]

    async def create_fraud_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist fraud event data.
        
        Args:
            event_data: The event data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.get_fraud_events_collection().insert_one(event_data)
        return event_data

    async def list_fraud_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        List fraud events records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.get_fraud_events_collection()
            .find({})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_fraud_events(self) -> int:
        """
        Count fraud events records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.get_fraud_events_collection().count_documents({})

    async def create_blocked_entity(
        self, entity_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create and persist blocked entity data.
        
        Args:
            entity_data: The entity data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.get_blocked_entities_collection().insert_one(entity_data)
        return entity_data

    async def find_active_blocked_entity(
        self,
        entity_type: str,
        entity_value: str,
    ) -> dict[str, Any] | None:
        """
        Fetch active blocked entity data from persistence.
        
        Args:
            entity_type: Blocked-entity type used by the operation.
            entity_value: The entity value value used by this operation.
        
        Returns:
            Matching record or value when available.
        """
        if not entity_value:
            return None
        return await self.get_blocked_entities_collection().find_one(
            {
                "entity_type": entity_type,
                "entity_value": entity_value,
                "is_active": True,
            }
        )

    async def count_blocked_entities(self) -> int:
        """
        Count blocked entities records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.get_blocked_entities_collection().count_documents(
            {"is_active": True}
        )


async def ensure_fraud_indexes() -> None:
    """
    Ensure the required database indexes exist for this repository.
    
    Returns:
        None.
    """
    fraud_events = FraudRepository().get_fraud_events_collection()
    await fraud_events.create_index(
        [("visitor_id", ASCENDING)],
        name="idx_fraud_events_visitor_id",
    )
    await fraud_events.create_index(
        [("event_type", ASCENDING)],
        name="idx_fraud_events_event_type",
    )
    await fraud_events.create_index(
        [("severity", ASCENDING)],
        name="idx_fraud_events_severity",
    )
    await fraud_events.create_index(
        [("created_at", DESCENDING)],
        name="idx_fraud_events_created_at",
    )

    blocked_entities = FraudRepository().get_blocked_entities_collection()
    await blocked_entities.create_index(
        [("entity_type", ASCENDING), ("entity_value", ASCENDING), ("is_active", ASCENDING)],
        name="idx_blocked_entities_lookup",
    )
    await blocked_entities.create_index(
        [("created_at", DESCENDING)],
        name="idx_blocked_entities_created_at",
    )
    await blocked_entities.create_index(
        [("expires_at", ASCENDING)],
        name="idx_blocked_entities_expires_at",
    )
    logger.info("Ensured fraud collection indexes")
