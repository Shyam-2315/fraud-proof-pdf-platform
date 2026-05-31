import logging
import re
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from app.models.request_log import REQUEST_LOG_COLLECTION
from app.utils.security import generate_uuid, utc_now

logger = logging.getLogger(__name__)


class RequestLogRepository:
    """Persist sanitized API request telemetry for admin observability."""

    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection used for request logs.

        Returns:
            Motor collection for sanitized request-log documents.
        """
        return get_database()[REQUEST_LOG_COLLECTION]

    async def create_log(self, log_data: dict[str, Any]) -> dict[str, Any]:
        """
        Store one sanitized API request log.

        Args:
            log_data: Request metadata without headers, bodies, cookies, or query strings.

        Returns:
            Persisted request-log document.
        """
        now = utc_now()
        document = {
            "_id": generate_uuid(),
            "created_at": now,
            **log_data,
        }
        await self.get_collection().insert_one(document)
        return document

    async def list_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        method: str | None = None,
        status_code: int | None = None,
        path: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return recent request logs filtered for the admin observability page.

        Args:
            limit: Maximum number of logs to return.
            offset: Number of matching rows to skip.
            method: Optional HTTP method filter.
            status_code: Optional response status-code filter.
            path: Optional case-insensitive path substring.

        Returns:
            Request-log documents sorted newest first.
        """
        query = _build_request_log_query(
            method=method,
            status_code=status_code,
            path=path,
        )
        cursor = (
            self.get_collection()
            .find(query)
            .sort("created_at", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_logs(
        self,
        method: str | None = None,
        status_code: int | None = None,
        path: str | None = None,
    ) -> int:
        """
        Count request logs matching the same filters as the admin list.

        Args:
            method: Optional HTTP method filter.
            status_code: Optional response status-code filter.
            path: Optional case-insensitive path substring.

        Returns:
            Number of matching request-log documents.
        """
        query = _build_request_log_query(
            method=method,
            status_code=status_code,
            path=path,
        )
        return await self.get_collection().count_documents(query)


def _build_request_log_query(
    method: str | None = None,
    status_code: int | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if method:
        query["method"] = method.upper()
    if status_code is not None:
        query["status_code"] = status_code
    if path:
        query["path"] = {"$regex": re.escape(path), "$options": "i"}
    return query


async def ensure_request_log_indexes() -> None:
    """Create MongoDB indexes required for recent request-log queries."""
    collection = RequestLogRepository().get_collection()
    await collection.create_index(
        [("request_id", ASCENDING)],
        name="idx_request_logs_request_id",
    )
    await collection.create_index(
        [("created_at", DESCENDING)],
        name="idx_request_logs_created_at",
    )
    await collection.create_index(
        [("status_code", ASCENDING), ("created_at", DESCENDING)],
        name="idx_request_logs_status_created",
    )
    await collection.create_index(
        [("method", ASCENDING), ("created_at", DESCENDING)],
        name="idx_request_logs_method_created",
    )
    await collection.create_index(
        [("path", ASCENDING), ("created_at", DESCENDING)],
        name="idx_request_logs_path_created",
    )
    logger.info("Ensured request log collection indexes")
