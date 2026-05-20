import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.fraud_event import ADMIN_AUDIT_LOGS_COLLECTION

logger = logging.getLogger(__name__)


class AdminAuditRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[ADMIN_AUDIT_LOGS_COLLECTION]

    async def create(self, audit_data: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(audit_data)
        return audit_data

    async def count_logs(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.get_collection().count_documents(filter_query or {})

    async def list_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self.get_collection().find({}).sort("created_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)


async def ensure_admin_audit_indexes() -> None:
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
