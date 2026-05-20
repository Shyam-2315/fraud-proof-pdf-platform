import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database import get_database
from app.models.risk import IP_INTELLIGENCE_COLLECTION, RISK_SCORE_SNAPSHOTS_COLLECTION

logger = logging.getLogger(__name__)


class RiskScoreSnapshotRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[RISK_SCORE_SNAPSHOTS_COLLECTION]

    async def create(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(snapshot)
        return snapshot

    async def list_by_visitor_id(
        self,
        visitor_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection()
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


class IPIntelligenceRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[IP_INTELLIGENCE_COLLECTION]

    async def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        insert_fields = {
            "_id": record.pop("_id", record.get("id")),
            "id": record.pop("id", record.get("_id")),
        }
        return await self.get_collection().find_one_and_update(
            {"ip_address": record["ip_address"]},
            {"$set": record, "$setOnInsert": insert_fields},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def get_by_ip(self, ip_address: str) -> dict[str, Any] | None:
        if not ip_address:
            return None
        return await self.get_collection().find_one({"ip_address": ip_address})

    async def list_by_ips(self, ip_addresses: list[str]) -> list[dict[str, Any]]:
        if not ip_addresses:
            return []
        cursor = self.get_collection().find({"ip_address": {"$in": ip_addresses}})
        return await cursor.to_list(length=len(ip_addresses))


async def ensure_risk_indexes() -> None:
    snapshots = RiskScoreSnapshotRepository().get_collection()
    await snapshots.create_index(
        [("visitor_id", ASCENDING)],
        name="idx_risk_snapshots_visitor_id",
    )
    await snapshots.create_index(
        [("score", DESCENDING)],
        name="idx_risk_snapshots_score",
    )
    await snapshots.create_index(
        [("level", ASCENDING)],
        name="idx_risk_snapshots_level",
    )
    await snapshots.create_index(
        [("created_at", DESCENDING)],
        name="idx_risk_snapshots_created_at",
    )

    ip_intel = IPIntelligenceRepository().get_collection()
    await ip_intel.create_index(
        [("ip_address", ASCENDING)],
        name="idx_ip_intelligence_ip_unique",
        unique=True,
    )
    await ip_intel.create_index(
        [("risk_score", DESCENDING)],
        name="idx_ip_intelligence_risk_score",
    )
    await ip_intel.create_index(
        [("checked_at", DESCENDING)],
        name="idx_ip_intelligence_checked_at",
    )
    logger.info("Ensured risk collection indexes")
