import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.fraud_event import ADMIN_AUDIT_LOGS_COLLECTION

logger = logging.getLogger(__name__)


class AdminAuditRepository:
    """Persist and query admin audit-log documents."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection storing admin audit logs.

        Returns:
            Motor collection for admin audit-log documents.
        """
        return get_database()[ADMIN_AUDIT_LOGS_COLLECTION]

    async def create(self, audit_data: dict[str, Any]) -> dict[str, Any]:
        """
        Insert an admin audit-log document.

        Args:
            audit_data: Audit log payload to persist.

        Returns:
            Inserted audit log document.
        """
        await self.get_collection().insert_one(audit_data)
        return audit_data

    async def count_logs(self, filter_query: dict[str, Any] | None = None) -> int:
        """
        Count admin audit logs matching an optional filter.

        Args:
            filter_query: Optional MongoDB filter query.

        Returns:
            Number of matching audit log documents.
        """
        return await self.get_collection().count_documents(filter_query or {})

    async def list_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Return recent admin audit logs ordered by creation time.

        Args:
            limit: Maximum number of audit logs to return.

        Returns:
            List of recent audit log documents.
        """
        cursor = self.get_collection().find({}).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)


async def ensure_admin_audit_indexes() -> None:
    """Create MongoDB indexes required for admin audit-log queries."""
    collection = AdminAuditRepository().get_collection()
    await collection.create_index(
        [("created_at", DESCENDING)],
        name="idx_admin_audit_logs_created_at",
    )
    await collection.create_index(
        [("action", ASCENDING)],
        name="idx_admin_audit_logs_action",
    )
    logger.info("Ensured admin audit log collection indexes")
