from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DESCENDING

from app.database import get_database
from app.models.fraud import BLOCKED_ENTITIES_COLLECTION, FRAUD_EVENTS_COLLECTION
from app.models.pdf import GENERATED_PDF_COLLECTION, PDFGenerationType
from app.models.user import USER_COLLECTION
from app.models.visitor import VISITOR_COLLECTION


class AdminRepository:
    """
    Repository that encapsulates database access for the domain model.
    """
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """
        Return the MongoDB collection used for the requested repository operation.
        
        Args:
            collection_name: Name of the MongoDB collection to query.
        
        Returns:
            Matching record or value when available.
        """
        return get_database()[collection_name]

    async def count_documents(
        self,
        collection_name: str,
        filter_query: dict[str, Any] | None = None,
    ) -> int:
        """
        Count documents records that match the requested filters.
        
        Args:
            collection_name: Name of the MongoDB collection to query.
            filter_query: MongoDB filter document applied to the query.
        
        Returns:
            Total number of matching records.
        """
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
        """
        List documents records that match the requested filters.
        
        Args:
            collection_name: Name of the MongoDB collection to query.
            filter_query: MongoDB filter document applied to the query.
            sort_field: Document field used to sort the result set.
            sort_direction: PyMongo sort direction constant applied to the query.
            limit: Maximum number of records or results to return.
            offset: Number of records to skip before returning results.
        
        Returns:
            List of matching records.
        """
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
        """
        Fetch document by id data from persistence.
        
        Args:
            collection_name: Name of the MongoDB collection to query.
            document_id: Unique identifier of the document to load.
        
        Returns:
            Matching record or value when available.
        """
        if not document_id:
            return None
        return await self.get_collection(collection_name).find_one({"_id": document_id})

    async def count_visitors(self) -> int:
        """
        Count visitors records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(VISITOR_COLLECTION)

    async def count_users(self) -> int:
        """
        Count users records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(USER_COLLECTION)

    async def count_pdfs(self) -> int:
        """
        Count pdfs records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(GENERATED_PDF_COLLECTION)

    async def count_anonymous_pdfs(self) -> int:
        """
        Count anonymous pdfs records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(
            GENERATED_PDF_COLLECTION,
            {"generation_type": PDFGenerationType.ANONYMOUS.value},
        )

    async def count_authenticated_pdfs(self) -> int:
        """
        Count authenticated pdfs records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(
            GENERATED_PDF_COLLECTION,
            {"generation_type": PDFGenerationType.AUTHENTICATED.value},
        )

    async def count_blocked_visitors(self) -> int:
        """
        Count blocked visitors records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(VISITOR_COLLECTION, {"is_blocked": True})

    async def count_high_risk_visitors(self) -> int:
        """
        Count high risk visitors records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(
            VISITOR_COLLECTION,
            {"$or": [{"risk_level": "HIGH"}, {"risk_score": {"$gte": 70}}]},
        )

    async def count_fraud_events(self) -> int:
        """
        Count fraud events records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(FRAUD_EVENTS_COLLECTION)

    async def count_blocked_entities(self) -> int:
        """
        Count blocked entities records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(
            BLOCKED_ENTITIES_COLLECTION,
            {"is_active": True},
        )

    async def count_converted_users(self) -> int:
        """
        Count converted users records that match the requested filters.
        
        Returns:
            Total number of matching records.
        """
        return await self.count_documents(
            USER_COLLECTION,
            {"linked_visitor_ids.0": {"$exists": True}},
        )

    async def list_recent_visitors(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        List recent visitors records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        return await self.list_documents(
            VISITOR_COLLECTION,
            sort_field="last_seen_at",
            limit=limit,
        )

    async def list_recent_users(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        List recent users records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        return await self.list_documents(USER_COLLECTION, limit=limit)

    async def list_recent_pdfs(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        List recent pdfs records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        return await self.list_documents(GENERATED_PDF_COLLECTION, limit=limit)

    async def list_recent_fraud_events(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        List recent fraud events records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        return await self.list_documents(FRAUD_EVENTS_COLLECTION, limit=limit)

    async def list_visitors(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_level: str | None = None,
        is_blocked: bool | None = None,
    ) -> list[dict[str, Any]]:
        """
        List visitors records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
            offset: Number of records to skip before returning results.
            risk_level: Risk level filter or value used by the operation.
            is_blocked: Boolean flag indicating whether blocked should be applied.
        
        Returns:
            List of matching records.
        """
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
        """
        List users records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
            offset: Number of records to skip before returning results.
        
        Returns:
            List of matching records.
        """
        return await self.list_documents(USER_COLLECTION, limit=limit, offset=offset)

    async def list_pdfs(
        self,
        limit: int = 50,
        offset: int = 0,
        generation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List pdfs records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
            offset: Number of records to skip before returning results.
            generation_type: PDF generation type filter used by the operation.
        
        Returns:
            List of matching records.
        """
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
        """
        List fraud events records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
            offset: Number of records to skip before returning results.
            severity: Severity filter or value used by the operation.
            event_type: Event type filter or value used by the operation.
        
        Returns:
            List of matching records.
        """
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
        """
        List blocked entities records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
            offset: Number of records to skip before returning results.
            entity_type: Blocked-entity type used by the operation.
            is_active: Whether to restrict the operation to active records.
        
        Returns:
            List of matching records.
        """
        return await self.list_documents(
            BLOCKED_ENTITIES_COLLECTION,
            _remove_none({"entity_type": entity_type, "is_active": is_active}),
            limit=limit,
            offset=offset,
        )


def _remove_none(values: dict[str, Any]) -> dict[str, Any]:
    """
    Remove None for the requested operation.
    
    Args:
        values: Mapping of values processed by the helper.
    
    Returns:
        Operation result represented as `dict[str, Any]`.
    """
    return {key: value for key, value in values.items() if value is not None}
