import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database import get_database
from app.models.visitor import VISITOR_COLLECTION
from app.utils.security import utc_now

logger = logging.getLogger(__name__)


class VisitorRepository:
    """
    Repository that encapsulates database access for the domain model.
    """
    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection used for the requested repository operation.
        
        Returns:
            Matching record or value when available.
        """
        return get_database()[VISITOR_COLLECTION]

    async def find_by_cookie_id(self, cookie_id: str | None) -> dict[str, Any] | None:
        """
        Fetch by cookie id data from persistence.
        
        Args:
            cookie_id: Unique cookie identifier used by the operation.
        
        Returns:
            Matching record or value when available.
        """
        if not cookie_id:
            return None
        return await self.get_collection().find_one(
            {"$or": [{"cookie_id": cookie_id}, {"cookie_ids": cookie_id}]}
        )

    async def find_by_local_storage_id(
        self, local_storage_id: str | None
    ) -> dict[str, Any] | None:
        """
        Fetch by local storage id data from persistence.
        
        Args:
            local_storage_id: Unique local storage identifier used by the operation.
        
        Returns:
            Matching record or value when available.
        """
        if not local_storage_id:
            return None
        return await self.get_collection().find_one(
            {"local_storage_ids": local_storage_id}
        )

    async def find_by_session_id(self, session_id: str | None) -> dict[str, Any] | None:
        """
        Fetch by session id data from persistence.
        
        Args:
            session_id: Unique session identifier used by the operation.
        
        Returns:
            Matching record or value when available.
        """
        if not session_id:
            return None
        return await self.get_collection().find_one({"session_ids": session_id})

    async def find_by_fingerprint_hash(
        self, fingerprint_hash: str | None
    ) -> dict[str, Any] | None:
        """
        Fetch by fingerprint hash data from persistence.
        
        Args:
            fingerprint_hash: Device fingerprint hash associated with the caller.
        
        Returns:
            Matching record or value when available.
        """
        if not fingerprint_hash:
            return None
        return await self.get_collection().find_one(
            {"fingerprint_hashes": fingerprint_hash}
        )

    async def find_by_device_profile_hash(
        self, device_profile_hash: str | None
    ) -> dict[str, Any] | None:
        """
        Fetch by device profile hash data from persistence.
        
        Args:
            device_profile_hash: Hash value representing device profile.
        
        Returns:
            Matching record or value when available.
        """
        if not device_profile_hash:
            return None
        return await self.get_collection().find_one(
            {"device_profile_hashes": device_profile_hash}
        )

    async def find_by_canvas_hash(self, canvas_hash: str | None) -> dict[str, Any] | None:
        """
        Fetch by canvas hash data from persistence.
        
        Args:
            canvas_hash: Hash value representing canvas.
        
        Returns:
            Matching record or value when available.
        """
        if not canvas_hash:
            return None
        return await self.get_collection().find_one({"canvas_hashes": canvas_hash})

    async def find_by_webgl_hash(self, webgl_hash: str | None) -> dict[str, Any] | None:
        """
        Fetch by webgl hash data from persistence.
        
        Args:
            webgl_hash: Hash value representing webgl.
        
        Returns:
            Matching record or value when available.
        """
        if not webgl_hash:
            return None
        return await self.get_collection().find_one({"webgl_hashes": webgl_hash})

    async def find_by_ip_and_user_agent(
        self,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict[str, Any] | None:
        """
        Fetch by ip and user agent data from persistence.
        
        Args:
            ip_address: IP address being analyzed or persisted.
            user_agent: User-Agent string supplied by the client.
        
        Returns:
            Matching record or value when available.
        """
        if not ip_address or not user_agent:
            return None
        return await self.get_collection().find_one(
            {"ip_addresses": ip_address, "user_agents": user_agent}
        )

    async def find_best_match(
        self,
        cookie_id: str | None,
        local_storage_id: str | None,
        session_id: str | None,
        fingerprint_hash: str | None,
        device_profile_hash: str | None = None,
        canvas_hash: str | None = None,
        webgl_hash: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch best match data from persistence.
        
        Args:
            cookie_id: Unique cookie identifier used by the operation.
            local_storage_id: Unique local storage identifier used by the operation.
            session_id: Unique session identifier used by the operation.
            fingerprint_hash: Device fingerprint hash associated with the caller.
            device_profile_hash: Hash value representing device profile.
            canvas_hash: Hash value representing canvas.
            webgl_hash: Hash value representing webgl.
        
        Returns:
            Matching record or value when available.
        """
        match = await self.find_by_cookie_id(cookie_id)
        if match is not None:
            return match

        match = await self.find_by_local_storage_id(local_storage_id)
        if match is not None:
            return match

        match = await self.find_by_fingerprint_hash(fingerprint_hash)
        if match is not None:
            return match

        return None

    async def find_weak_identity_match(
        self,
        device_profile_hash: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> dict[str, Any] | None:
        """
        Fetch weak identity match data from persistence.
        
        Args:
            device_profile_hash: Hash value representing device profile.
            ip_address: IP address being analyzed or persisted.
            user_agent: User-Agent string supplied by the client.
        
        Returns:
            Matching record or value when available.
        """
        match = await self.find_by_device_profile_hash(device_profile_hash)
        if match is not None:
            return match
        return await self.find_by_ip_and_user_agent(ip_address, user_agent)

    async def create_visitor(self, visitor_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist visitor data.
        
        Args:
            visitor_data: The visitor data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.get_collection().insert_one(visitor_data)
        return visitor_data

    async def update_visitor(
        self,
        visitor_id: str,
        update_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Update persisted visitor data.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
            update_data: The update data value used by this operation.
        
        Returns:
            Updated result of the operation.
        """
        if update_data:
            await self.get_collection().update_one(
                {"_id": visitor_id},
                {"$set": update_data},
            )
        return await self.get_by_id(visitor_id)

    async def get_by_id(self, visitor_id: str) -> dict[str, Any] | None:
        """
        Fetch by id data from persistence.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
        
        Returns:
            Matching record or value when available.
        """
        if not visitor_id:
            return None
        return await self.get_collection().find_one({"_id": visitor_id})

    async def list_by_ids(self, visitor_ids: list[str]) -> list[dict[str, Any]]:
        """
        List by ids records that match the requested filters.
        
        Args:
            visitor_ids: Collection of visitor identifiers processed by the operation.
        
        Returns:
            List of matching records.
        """
        visitor_ids = [visitor_id for visitor_id in visitor_ids if visitor_id]
        if not visitor_ids:
            return []
        cursor = self.get_collection().find({"_id": {"$in": visitor_ids}})
        return await cursor.to_list(length=len(visitor_ids))

    async def increment_free_usage(self, visitor_id: str) -> dict[str, Any] | None:
        """
        Increment Free Usage for the requested operation.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
        
        Returns:
            Operation result represented as `dict[str, Any] | None`.
        """
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
        """
        Mark persisted visitor blocked data with the requested state.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
            reason: The reason value used by this operation.
        
        Returns:
            Updated result of the operation.
        """
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
        """
        Count visitors records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.get_collection().count_documents({})

    async def count_documents(self, filter_query: dict[str, Any] | None = None) -> int:
        """
        Count documents records that match the requested filters.
        
        Args:
            filter_query: MongoDB filter document applied to the query.
        
        Returns:
            Total number of matching records.
        """
        return await self.get_collection().count_documents(filter_query or {})

    async def count_blocked_visitors(self) -> int:
        """
        Count blocked visitors records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.get_collection().count_documents({"is_blocked": True})

    async def count_high_risk_visitors(self) -> int:
        """
        Count high risk visitors records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.get_collection().count_documents({"risk_score": {"$gte": 60}})

    async def count_by_ip(self, ip_address: str | None) -> int:
        """
        Count by ip records that match the requested filters.
        
        Args:
            ip_address: IP address being analyzed or persisted.
        
        Returns:
            Total number of matching records.
        """
        if not ip_address:
            return 0
        return await self.get_collection().count_documents({"ip_addresses": ip_address})

    async def list_for_admin_fraud(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        List for admin fraud records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.get_collection()
            .find({})
            .sort([("risk_score", DESCENDING), ("last_seen_at", DESCENDING)])
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


async def ensure_visitor_indexes() -> None:
    """
    Ensure the required database indexes exist for this repository.
    
    Returns:
        None.
    """
    collection = VisitorRepository().get_collection()
    await collection.create_index(
        [("cookie_id", ASCENDING)],
        name="idx_visitors_cookie_id_unique",
        unique=True,
        sparse=True,
    )
    await collection.create_index(
        [("cookie_ids", ASCENDING)],
        name="idx_visitors_cookie_ids",
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
        [("device_profile_hashes", ASCENDING)],
        name="idx_visitors_device_profile_hashes",
    )
    await collection.create_index(
        [("canvas_hashes", ASCENDING)],
        name="idx_visitors_canvas_hashes",
    )
    await collection.create_index(
        [("webgl_hashes", ASCENDING)],
        name="idx_visitors_webgl_hashes",
    )
    await collection.create_index(
        [("primary_fingerprint_hash", ASCENDING)],
        name="idx_visitors_primary_fingerprint_hash",
    )
    await collection.create_index(
        [("ip_addresses", ASCENDING)],
        name="idx_visitors_ip_addresses",
    )
    await collection.create_index(
        [("last_seen_at", ASCENDING)],
        name="idx_visitors_last_seen_at",
    )
    await collection.create_index(
        [("is_blocked", ASCENDING)],
        name="idx_visitors_is_blocked",
    )
    await collection.create_index(
        [("visitor_id", ASCENDING)],
        name="idx_visitors_visitor_id",
        sparse=True,
    )
    logger.info("Ensured visitor collection indexes")
