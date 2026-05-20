import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, ReturnDocument

from app.database import get_database
from app.models.user_usage import USER_USAGE_COLLECTION
from app.utils.security import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class UserUsageRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[USER_USAGE_COLLECTION]

    async def get_or_create_usage(
        self,
        user_id: str,
        plan: str,
        month_key: str,
        limit: int,
    ) -> dict[str, Any]:
        existing = await self.get_collection().find_one(
            {"user_id": user_id, "month_key": month_key}
        )
        if existing is not None:
            return existing
        now = utc_now()
        document = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "plan": plan,
            "month_key": month_key,
            "pdf_count": 0,
            "limit": limit,
            "created_at": now,
            "updated_at": now,
        }
        await self.get_collection().insert_one(document)
        return document

    async def increment_usage(
        self,
        user_id: str,
        plan: str,
        month_key: str,
        limit: int,
    ) -> dict[str, Any]:
        now = utc_now()
        return await self.get_collection().find_one_and_update(
            {"user_id": user_id, "month_key": month_key},
            {
                "$inc": {"pdf_count": 1},
                "$set": {"plan": plan, "limit": limit, "updated_at": now},
                "$setOnInsert": {"_id": generate_uuid(), "created_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )


async def ensure_user_usage_indexes() -> None:
    collection = UserUsageRepository().get_collection()
    await collection.create_index(
        [("user_id", ASCENDING), ("month_key", ASCENDING)],
        name="idx_user_usage_user_month_unique",
        unique=True,
    )
    await collection.create_index(
        [("month_key", ASCENDING)],
        name="idx_user_usage_month",
    )
    logger.info("Ensured user usage collection indexes")
