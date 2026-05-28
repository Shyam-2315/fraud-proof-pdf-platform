import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, ReturnDocument

from app.database import get_database
from app.models.user_usage import USER_USAGE_COLLECTION
from app.utils.security import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class UserUsageRepository:
    """Persist and update monthly authenticated user usage records."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection storing user usage counters.

        Returns:
            Motor collection for usage-counter documents.
        """
        return get_database()[USER_USAGE_COLLECTION]

    async def get_or_create_usage(
        self,
        user_id: str,
        plan: str,
        month_key: str,
        limit: int,
    ) -> dict[str, Any]:
        """
        Load or create the monthly usage record for a user.

        Args:
            user_id: User whose usage record should be loaded.
            plan: Current subscription plan for the usage record.
            month_key: Month bucket in ``YYYY-MM`` format.
            limit: Monthly PDF limit for the plan.

        Returns:
            Existing or newly created usage document.
        """
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
        """
        Increment the monthly PDF usage counter for a user.

        Args:
            user_id: User whose usage should be incremented.
            plan: Current subscription plan for the usage record.
            month_key: Month bucket in ``YYYY-MM`` format.
            limit: Monthly PDF limit for the plan.

        Returns:
            Updated usage document after incrementing the PDF count.
        """
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
    """Create MongoDB indexes required for monthly usage lookups."""
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
