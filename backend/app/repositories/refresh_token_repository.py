import hashlib
import logging
from datetime import datetime
from datetime import UTC
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING

from app.database import get_database
from app.models.refresh_token import REFRESH_TOKEN_COLLECTION
from app.utils.security import utc_now

logger = logging.getLogger(__name__)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshTokenRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[REFRESH_TOKEN_COLLECTION]

    async def create_token(
        self,
        token_id: str,
        user_id: str,
        token: str,
        expires_at: datetime,
    ) -> dict[str, Any]:
        document = {
            "_id": token_id,
            "user_id": user_id,
            "token_hash": hash_refresh_token(token),
            "expires_at": expires_at,
            "revoked": False,
            "created_at": utc_now(),
        }
        await self.get_collection().insert_one(document)
        return document

    async def find_active_by_token(self, token: str) -> dict[str, Any] | None:
        document = await self.get_collection().find_one(
            {"token_hash": hash_refresh_token(token), "revoked": False}
        )
        if document is None:
            return None
        expires_at = document["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= utc_now():
            await self.revoke_by_id(document["_id"])
            return None
        return document

    async def revoke_by_id(self, token_id: str) -> None:
        await self.get_collection().update_one(
            {"_id": token_id},
            {"$set": {"revoked": True}},
        )

    async def revoke_by_token(self, token: str) -> None:
        await self.get_collection().update_one(
            {"token_hash": hash_refresh_token(token)},
            {"$set": {"revoked": True}},
        )


async def ensure_refresh_token_indexes() -> None:
    collection = RefreshTokenRepository().get_collection()
    await collection.create_index(
        [("token_hash", ASCENDING)],
        name="idx_refresh_tokens_token_hash",
        unique=True,
    )
    await collection.create_index(
        [("user_id", ASCENDING)],
        name="idx_refresh_tokens_user_id",
    )
    await collection.create_index(
        [("expires_at", ASCENDING)],
        name="idx_refresh_tokens_expires_at",
    )
    logger.info("Ensured refresh token collection indexes")
