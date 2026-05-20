from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING

from app.database import get_database
from app.models.fraud import BLOCKED_ENTITIES_COLLECTION, FRAUD_EVENTS_COLLECTION
from app.models.pdf import GENERATED_PDF_COLLECTION, PDFGenerationType
from app.models.user import USER_COLLECTION
from app.models.visitor import VISITOR_COLLECTION


class AdminRepository:
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        return get_database()[collection_name]

    async def count_documents(
        self,
        collection_name: str,
        filter_query: dict[str, Any] | None = None,
    ) -> int:
        return await self.get_collection(collection_name).count_documents(
            filter_query or {}
        )

    async def list_documents(
        self,
        collection_name: str,
        filter_query: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_direction: int = DESCENDING,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.get_collection(collection_name)
            .find(filter_query or {})
            .sort(sort_field, sort_direction)
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_document_by_id(
        self,
        collection_name: str,
        document_id: str,
    ) -> dict[str, Any] | None:
        if not document_id:
            return None
        return await self.get_collection(collection_name).find_one({"_id": document_id})

    async def count_visitors(self) -> int:
        return await self.count_documents(VISITOR_COLLECTION)

    async def count_users(self) -> int:
        return await self.count_documents(USER_COLLECTION)

    async def count_pdfs(self) -> int:
        return await self.count_documents(GENERATED_PDF_COLLECTION)

    async def count_anonymous_pdfs(self) -> int:
        return await self.count_documents(
            GENERATED_PDF_COLLECTION,
            {"generation_type": PDFGenerationType.ANONYMOUS.value},
        )

    async def count_authenticated_pdfs(self) -> int:
        return await self.count_documents(
            GENERATED_PDF_COLLECTION,
            {"generation_type": PDFGenerationType.AUTHENTICATED.value},
        )

    async def count_blocked_visitors(self) -> int:
        return await self.count_documents(VISITOR_COLLECTION, {"is_blocked": True})

    async def count_high_risk_visitors(self) -> int:
        return await self.count_documents(
            VISITOR_COLLECTION,
            {"$or": [{"risk_level": "HIGH"}, {"risk_score": {"$gte": 70}}]},
        )

    async def count_fraud_events(self) -> int:
        return await self.count_documents(FRAUD_EVENTS_COLLECTION)

    async def count_blocked_entities(self) -> int:
        return await self.count_documents(
            BLOCKED_ENTITIES_COLLECTION,
            {"is_active": True},
        )

    async def count_converted_users(self) -> int:
        return await self.count_documents(
            USER_COLLECTION,
            {"linked_visitor_ids.0": {"$exists": True}},
        )

    async def list_recent_visitors(self, limit: int = 5) -> list[dict[str, Any]]:
        return await self.list_documents(
            VISITOR_COLLECTION,
            sort_field="last_seen_at",
            limit=limit,
        )

    async def list_recent_users(self, limit: int = 5) -> list[dict[str, Any]]:
        return await self.list_documents(USER_COLLECTION, limit=limit)

    async def list_recent_pdfs(self, limit: int = 5) -> list[dict[str, Any]]:
        return await self.list_documents(GENERATED_PDF_COLLECTION, limit=limit)

    async def list_recent_fraud_events(self, limit: int = 5) -> list[dict[str, Any]]:
        return await self.list_documents(FRAUD_EVENTS_COLLECTION, limit=limit)

    async def list_visitors(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_level: str | None = None,
        is_blocked: bool | None = None,
    ) -> list[dict[str, Any]]:
        return await self.list_documents(
            VISITOR_COLLECTION,
            _remove_none({"risk_level": risk_level, "is_blocked": is_blocked}),
            sort_field="last_seen_at",
            limit=limit,
            offset=offset,
        )

    async def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.list_documents(USER_COLLECTION, limit=limit, offset=offset)

    async def list_pdfs(
        self,
        limit: int = 50,
        offset: int = 0,
        generation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self.list_documents(
            GENERATED_PDF_COLLECTION,
            _remove_none({"generation_type": generation_type}),
            limit=limit,
            offset=offset,
        )

    async def list_fraud_events(
        self,
        limit: int = 50,
        offset: int = 0,
        severity: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self.list_documents(
            FRAUD_EVENTS_COLLECTION,
            _remove_none({"severity": severity, "event_type": event_type}),
            limit=limit,
            offset=offset,
        )

    async def list_blocked_entities(
        self,
        limit: int = 50,
        offset: int = 0,
        entity_type: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict[str, Any]]:
        return await self.list_documents(
            BLOCKED_ENTITIES_COLLECTION,
            _remove_none({"entity_type": entity_type, "is_active": is_active}),
            limit=limit,
            offset=offset,
        )


def _remove_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
