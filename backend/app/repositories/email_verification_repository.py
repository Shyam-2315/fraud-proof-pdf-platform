import logging
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database import get_database
from app.models.email_verification import EMAIL_VERIFICATION_COLLECTION
from app.utils.security import utc_now

logger = logging.getLogger(__name__)


class EmailVerificationRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[EMAIL_VERIFICATION_COLLECTION]

    async def create_verification(self, document: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(document)
        return document

    async def find_latest_by_email(self, email: str) -> dict[str, Any] | None:
        if not email:
            return None
        return await self.get_collection().find_one(
            {"email": email},
            sort=[("created_at", DESCENDING)],
        )

    async def find_latest_unconsumed_by_email(self, email: str) -> dict[str, Any] | None:
        if not email:
            return None
        return await self.get_collection().find_one(
            {"email": email, "consumed": False},
            sort=[("created_at", DESCENDING)],
        )

    async def consume_all_for_email(self, email: str) -> None:
        if not email:
            return
        await self.get_collection().update_many(
            {"email": email, "consumed": False},
            {"$set": {"consumed": True, "updated_at": utc_now()}},
        )

    async def increment_attempts(self, verification_id: str, consume: bool = False) -> dict[str, Any] | None:
        update: dict[str, Any] = {
            "$inc": {"attempts": 1},
            "$set": {"updated_at": utc_now()},
        }
        if consume:
            update["$set"]["consumed"] = True
        return await self.get_collection().find_one_and_update(
            {"_id": verification_id},
            update,
            return_document=ReturnDocument.AFTER,
        )

    async def consume(self, verification_id: str) -> dict[str, Any] | None:
        return await self.get_collection().find_one_and_update(
            {"_id": verification_id},
            {"$set": {"consumed": True, "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )

    async def mark_expired(self, verification_id: str) -> dict[str, Any] | None:
        return await self.consume(verification_id)

    async def list_by_email(self, email: str, limit: int = 20) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection()
            .find({"email": email})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


async def ensure_email_verification_indexes() -> None:
    collection = EmailVerificationRepository().get_collection()
    await collection.create_index(
        [("email", ASCENDING)],
        name="idx_email_verifications_email",
    )
    await collection.create_index(
        [("user_id", ASCENDING)],
        name="idx_email_verifications_user_id",
    )
    await collection.create_index(
        [("expires_at", ASCENDING)],
        name="idx_email_verifications_expires_at",
    )
    await collection.create_index(
        [("consumed", ASCENDING)],
        name="idx_email_verifications_consumed",
    )
    await collection.create_index(
        [("email", ASCENDING), ("created_at", DESCENDING)],
        name="idx_email_verifications_email_created_at",
    )
    logger.info("Ensured email verification collection indexes")
