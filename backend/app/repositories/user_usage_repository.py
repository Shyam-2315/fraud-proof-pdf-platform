import logging
from typing import Any
from datetime import datetime

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
        billing_period_start: datetime,
        billing_period_end: datetime,
    ) -> dict[str, Any]:
        """
        Load or create the monthly usage record for a user.

        Args:
            user_id: User whose usage record should be loaded.
            plan: Current subscription plan for the usage record.
            month_key: Month bucket in ``YYYY-MM`` format.
            limit: Monthly PDF limit for the plan.
            billing_period_start: Inclusive UTC start of the billing period.
            billing_period_end: Exclusive UTC end of the billing period.

        Returns:
            Existing or newly created usage document.
        """
        existing = await self.get_collection().find_one(
            {"user_id": user_id, "month_key": month_key}
        )
        if existing is not None:
            updates: dict[str, Any] = {}
            if existing.get("plan") != plan:
                updates["plan"] = plan
            if int(existing.get("limit", limit)) != limit:
                updates["limit"] = limit
            if existing.get("billing_period_start") != billing_period_start:
                updates["billing_period_start"] = billing_period_start
            if existing.get("billing_period_end") != billing_period_end:
                updates["billing_period_end"] = billing_period_end
            if updates:
                updates["updated_at"] = utc_now()
                return await self.get_collection().find_one_and_update(
                    {"_id": existing["_id"]},
                    {"$set": updates},
                    return_document=ReturnDocument.AFTER,
                )
            return existing
        now = utc_now()
        document = {
            "_id": generate_uuid(),
            "user_id": user_id,
            "plan": plan,
            "month_key": month_key,
            "pdf_count": 0,
            "limit": limit,
            "billing_period_start": billing_period_start,
            "billing_period_end": billing_period_end,
            "created_at": now,
            "updated_at": now,
        }
        await self.get_collection().insert_one(document)
        return document

    async def find_usage(self, user_id: str, month_key: str) -> dict[str, Any] | None:
        """
        Load an existing usage record without creating a new counter.

        Args:
            user_id: User whose usage record should be loaded.
            month_key: Month bucket in ``YYYY-MM`` format.

        Returns:
            Existing usage document, if present.
        """
        if not user_id or not month_key:
            return None
        return await self.get_collection().find_one(
            {"user_id": user_id, "month_key": month_key}
        )

    async def increment_usage(
        self,
        user_id: str,
        plan: str,
        month_key: str,
        limit: int,
        billing_period_start: datetime,
        billing_period_end: datetime,
    ) -> dict[str, Any]:
        """
        Increment the monthly PDF usage counter for a user.

        Args:
            user_id: User whose usage should be incremented.
            plan: Current subscription plan for the usage record.
            month_key: Month bucket in ``YYYY-MM`` format.
            limit: Monthly PDF limit for the plan.
            billing_period_start: Inclusive UTC start of the billing period.
            billing_period_end: Exclusive UTC end of the billing period.

        Returns:
            Updated usage document after incrementing the PDF count.
        """
        now = utc_now()
        return await self.get_collection().find_one_and_update(
            {"user_id": user_id, "month_key": month_key},
            {
                "$inc": {"pdf_count": 1},
                "$set": {
                    "plan": plan,
                    "limit": limit,
                    "billing_period_start": billing_period_start,
                    "billing_period_end": billing_period_end,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "_id": generate_uuid(),
                    "user_id": user_id,
                    "month_key": month_key,
                    "created_at": now,
                },
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
    await collection.create_index(
        [("billing_period_start", ASCENDING), ("billing_period_end", ASCENDING)],
        name="idx_user_usage_billing_period",
    )
    logger.info("Ensured user usage collection indexes")
