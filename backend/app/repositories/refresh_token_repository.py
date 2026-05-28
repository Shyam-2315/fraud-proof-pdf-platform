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
    """
    Hash a refresh token before persisting or comparing it.

    Args:
        token: Plain refresh token string.

    Returns:
        SHA-256 hex digest of the refresh token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshTokenRepository:
    """Persist and revoke refresh-token documents."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection storing refresh tokens.

        Returns:
            Motor collection for refresh-token documents.
        """
        return get_database()[REFRESH_TOKEN_COLLECTION]

    async def create_token(
        self,
        token_id: str,
        user_id: str,
        token: str,
        expires_at: datetime,
    ) -> dict[str, Any]:
        """
        Insert a refresh-token document.

        Args:
            token_id: Identifier of the refresh-token record.
            user_id: User who owns the refresh token.
            token: Plain refresh token to hash and persist.
            expires_at: Expiration timestamp for the refresh token.

        Returns:
            Inserted refresh-token document.
        """
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
        """
        Return an active, non-expired refresh-token document by plain token value.

        Args:
            token: Plain refresh token presented by the client.

        Returns:
            Active refresh-token document, or ``None`` when missing, revoked, or expired.
        """
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
        """
        Revoke a refresh token by its record identifier.

        Args:
            token_id: Refresh-token record identifier to revoke.
        """
        await self.get_collection().update_one(
            {"_id": token_id},
            {"$set": {"revoked": True}},
        )

    async def revoke_by_token(self, token: str) -> None:
        """
        Revoke a refresh token by its plain token value.

        Args:
            token: Plain refresh token to revoke.
        """
        await self.get_collection().update_one(
            {"token_hash": hash_refresh_token(token)},
            {"$set": {"revoked": True}},
        )


async def ensure_refresh_token_indexes() -> None:
    """Create MongoDB indexes required for refresh-token lookups."""
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
