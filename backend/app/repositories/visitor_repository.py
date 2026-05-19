import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, ReturnDocument

from app.database import get_database
from app.models.visitor import VISITOR_COLLECTION
from app.utils.security import utc_now

logger = logging.getLogger(__name__)


class VisitorRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[VISITOR_COLLECTION]

    async def find_by_cookie_id(self, cookie_id: str | None) -> dict[str, Any] | None:
        if not cookie_id:
            return None
        return await self.get_collection().find_one({"cookie_id": cookie_id})

    async def find_by_local_storage_id(
        self, local_storage_id: str | None
    ) -> dict[str, Any] | None:
        if not local_storage_id:
            return None
        return await self.get_collection().find_one(
            {"local_storage_ids": local_storage_id}
        )

    async def find_by_session_id(self, session_id: str | None) -> dict[str, Any] | None:
        if not session_id:
            return None
        return await self.get_collection().find_one({"session_ids": session_id})

    async def find_by_fingerprint_hash(
        self, fingerprint_hash: str | None
    ) -> dict[str, Any] | None:
        if not fingerprint_hash:
            return None
        return await self.get_collection().find_one(
            {"fingerprint_hashes": fingerprint_hash}
        )

    async def find_best_match(
        self,
        cookie_id: str | None,
        local_storage_id: str | None,
        session_id: str | None,
        fingerprint_hash: str | None,
    ) -> dict[str, Any] | None:
        match = await self.find_by_cookie_id(cookie_id)
        if match is not None:
            return match

        match = await self.find_by_local_storage_id(local_storage_id)
        if match is not None:
            return match

        match = await self.find_by_fingerprint_hash(fingerprint_hash)
        if match is not None:
            return match

        return await self.find_by_session_id(session_id)

    async def create_visitor(self, visitor_data: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(visitor_data)
        return visitor_data

    async def update_visitor(
        self,
        visitor_id: str,
        update_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        if update_data:
            await self.get_collection().update_one(
                {"_id": visitor_id},
                {"$set": update_data},
            )
        return await self.get_by_id(visitor_id)

    async def get_by_id(self, visitor_id: str) -> dict[str, Any] | None:
        if not visitor_id:
            return None
        return await self.get_collection().find_one({"_id": visitor_id})

    async def increment_free_usage(self, visitor_id: str) -> dict[str, Any] | None:
        return await self.get_collection().find_one_and_update(
            {"_id": visitor_id},
            {
                "$inc": {"free_usage_count": 1},
                "$set": {"last_seen_at": utc_now()},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def mark_visitor_blocked(
        self,
        visitor_id: str,
        reason: str,
    ) -> dict[str, Any] | None:
        return await self.get_collection().find_one_and_update(
            {"_id": visitor_id},
            {
                "$set": {
                    "is_blocked": True,
                    "block_reason": reason,
                    "last_seen_at": utc_now(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def count_visitors(self) -> int:
        return await self.get_collection().count_documents({})

    async def count_blocked_visitors(self) -> int:
        return await self.get_collection().count_documents({"is_blocked": True})

    async def count_high_risk_visitors(self) -> int:
        return await self.get_collection().count_documents({"risk_score": {"$gte": 70}})


async def ensure_visitor_indexes() -> None:
    collection = VisitorRepository().get_collection()
    await collection.create_index(
        [("cookie_id", ASCENDING)],
        name="idx_visitors_cookie_id_unique",
        unique=True,
        sparse=True,
    )
    await collection.create_index(
        [("local_storage_ids", ASCENDING)],
        name="idx_visitors_local_storage_ids",
    )
    await collection.create_index(
        [("session_ids", ASCENDING)],
        name="idx_visitors_session_ids",
    )
    await collection.create_index(
        [("fingerprint_hashes", ASCENDING)],
        name="idx_visitors_fingerprint_hashes",
    )
    await collection.create_index(
        [("primary_fingerprint_hash", ASCENDING)],
        name="idx_visitors_primary_fingerprint_hash",
    )
    await collection.create_index(
        [("last_seen_at", ASCENDING)],
        name="idx_visitors_last_seen_at",
    )
    logger.info("Ensured visitor collection indexes")
