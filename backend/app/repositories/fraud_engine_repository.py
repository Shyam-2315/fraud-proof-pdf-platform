import logging
import re
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.database import get_database

logger = logging.getLogger(__name__)

FRAUD_FEATURE_SNAPSHOTS_COLLECTION = "fraud_feature_snapshots"
FRAUD_TRAINING_EVENTS_COLLECTION = "fraud_training_events"
FRAUD_LABELS_COLLECTION = "fraud_labels"
ML_MODEL_VERSIONS_COLLECTION = "ml_model_versions"
FRAUD_DECISIONS_COLLECTION = "fraud_decisions"


class FraudEngineRepository:
    """
    Repository that encapsulates database access for the domain model.
    """
    def collection(self, name: str) -> AsyncIOMotorCollection:
        """
        Collection for the requested operation.
        
        Args:
            name: The name value used by this operation.
        
        Returns:
            Operation result represented as `AsyncIOMotorCollection`.
        """
        return get_database()[name]

    async def create_feature_snapshot(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist feature snapshot data.
        
        Args:
            data: The data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.collection(FRAUD_FEATURE_SNAPSHOTS_COLLECTION).insert_one(data)
        return data

    async def list_feature_snapshots_by_visitor(
        self,
        visitor_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List feature snapshots by visitor records that match the requested filters.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.collection(FRAUD_FEATURE_SNAPSHOTS_COLLECTION)
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def create_training_event(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist training event data.
        
        Args:
            data: The data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.collection(FRAUD_TRAINING_EVENTS_COLLECTION).insert_one(data)
        return data

    async def count_training_events(self, filter_query: dict[str, Any] | None = None) -> int:
        """
        Count training events records that match the requested filters.
        
        Args:
            filter_query: MongoDB filter document applied to the query.
        
        Returns:
            Total number of matching records.
        """
        return await self.collection(FRAUD_TRAINING_EVENTS_COLLECTION).count_documents(
            filter_query or {}
        )

    async def list_training_events(
        self,
        filter_query: dict[str, Any] | None = None,
        limit: int = 100000,
    ) -> list[dict[str, Any]]:
        """
        List training events records that match the requested filters.
        
        Args:
            filter_query: MongoDB filter document applied to the query.
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.collection(FRAUD_TRAINING_EVENTS_COLLECTION)
            .find(filter_query or {})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def update_training_labels_for_visitor(
        self,
        visitor_id: str,
        label: int,
        source: str,
        confidence: float,
    ) -> int:
        """
        Update persisted training labels for visitor data.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
            label: The label value used by this operation.
            source: The source value used by this operation.
            confidence: The confidence value used by this operation.
        
        Returns:
            Updated result of the operation.
        """
        result = await self.collection(FRAUD_TRAINING_EVENTS_COLLECTION).update_many(
            {"visitor_id": visitor_id},
            {
                "$set": {
                    "outcome_label": label,
                    "label_source": source,
                    "label_confidence": confidence,
                }
            },
        )
        return int(result.modified_count)

    async def create_label(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist label data.
        
        Args:
            data: The data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.collection(FRAUD_LABELS_COLLECTION).insert_one(data)
        return data

    async def latest_label_for_visitor(self, visitor_id: str) -> dict[str, Any] | None:
        """
        Latest Label For Visitor for the requested operation.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
        
        Returns:
            Operation result represented as `dict[str, Any] | None`.
        """
        return await self.collection(FRAUD_LABELS_COLLECTION).find_one(
            {"visitor_id": visitor_id},
            sort=[("created_at", DESCENDING)],
        )

    async def list_labels(self, limit: int = 100000) -> list[dict[str, Any]]:
        """
        List labels records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.collection(FRAUD_LABELS_COLLECTION)
            .find({})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def create_model_version(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist model version data.
        
        Args:
            data: The data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.collection(ML_MODEL_VERSIONS_COLLECTION).insert_one(data)
        return data

    async def list_model_versions(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        List model versions records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.collection(ML_MODEL_VERSIONS_COLLECTION)
            .find({})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_model_version(self, model_version_id: str) -> dict[str, Any] | None:
        """
        Fetch model version data from persistence.
        
        Args:
            model_version_id: Unique model version identifier used by the operation.
        
        Returns:
            Matching record or value when available.
        """
        return await self.collection(ML_MODEL_VERSIONS_COLLECTION).find_one(
            {"_id": model_version_id}
        )

    async def update_model_status(
        self,
        model_version_id: str,
        status: str,
    ) -> dict[str, Any] | None:
        """
        Update persisted model status data.
        
        Args:
            model_version_id: Unique model version identifier used by the operation.
            status: The status value used by this operation.
        
        Returns:
            Updated result of the operation.
        """
        return await self.collection(ML_MODEL_VERSIONS_COLLECTION).find_one_and_update(
            {"_id": model_version_id},
            {"$set": {"status": status}},
            return_document=ReturnDocument.AFTER,
        )

    async def archive_active_models(self) -> int:
        """
        Archive Active Models for the requested operation.
        
        Returns:
            Operation result represented as `int`.
        """
        result = await self.collection(ML_MODEL_VERSIONS_COLLECTION).update_many(
            {"status": "ACTIVE"},
            {"$set": {"status": "ARCHIVED"}},
        )
        return int(result.modified_count)

    async def create_decision(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create and persist decision data.
        
        Args:
            data: The data value used by this operation.
        
        Returns:
            Constructed result for the requested operation.
        """
        await self.collection(FRAUD_DECISIONS_COLLECTION).insert_one(data)
        return data

    async def list_decisions_by_visitor(
        self,
        visitor_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List decisions by visitor records that match the requested filters.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
            limit: Maximum number of records or results to return.
        
        Returns:
            List of matching records.
        """
        cursor = (
            self.collection(FRAUD_DECISIONS_COLLECTION)
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def list_decisions(
        self,
        limit: int = 100,
        offset: int = 0,
        visitor_id: str | None = None,
        action_type: str | None = None,
        decision: str | None = None,
        risk_level: str | None = None,
        user_id: str | None = None,
        search: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        List decisions records that match the requested filters.
        
        Args:
            limit: Maximum number of records or results to return.
            offset: Number of matching rows to skip.
            visitor_id: Unique visitor identifier used by the operation.
            action_type: The action type value used by this operation.
            decision: Optional decision filter.
            risk_level: Optional risk-level filter.
            user_id: Optional user identifier filter.
            search: Optional visitor/user/action substring filter.
            created_from: Optional inclusive created-at lower bound.
            created_to: Optional exclusive created-at upper bound.
        
        Returns:
            List of matching records.
        """
        query = _build_decision_query(
            visitor_id=visitor_id,
            action_type=action_type,
            decision=decision,
            risk_level=risk_level,
            user_id=user_id,
            search=search,
            created_from=created_from,
            created_to=created_to,
        )
        cursor = (
            self.collection(FRAUD_DECISIONS_COLLECTION)
            .find(query)
            .sort("created_at", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_decisions(
        self,
        filter_query: dict[str, Any] | None = None,
        visitor_id: str | None = None,
        action_type: str | None = None,
        decision: str | None = None,
        risk_level: str | None = None,
        user_id: str | None = None,
        search: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> int:
        """
        Count decisions records that match the requested filters.
        
        Args:
            filter_query: MongoDB filter document applied to the query.
            visitor_id: Optional visitor identifier filter.
            action_type: Optional action-type filter.
            decision: Optional decision filter.
            risk_level: Optional risk-level filter.
            user_id: Optional user identifier filter.
            search: Optional visitor/user/action substring filter.
            created_from: Optional inclusive created-at lower bound.
            created_to: Optional exclusive created-at upper bound.
        
        Returns:
            Total number of matching records.
        """
        query = dict(filter_query or {})
        query.update(
            _build_decision_query(
                visitor_id=visitor_id,
                action_type=action_type,
                decision=decision,
                risk_level=risk_level,
                user_id=user_id,
                search=search,
                created_from=created_from,
                created_to=created_to,
            )
        )
        return await self.collection(FRAUD_DECISIONS_COLLECTION).count_documents(
            query
        )


async def ensure_fraud_engine_indexes() -> None:
    """
    Ensure the required database indexes exist for this repository.
    
    Returns:
        None.
    """
    repository = FraudEngineRepository()

    feature_snapshots = repository.collection(FRAUD_FEATURE_SNAPSHOTS_COLLECTION)
    await feature_snapshots.create_index([("visitor_id", ASCENDING)], name="idx_feature_snapshots_visitor")
    await feature_snapshots.create_index([("action_type", ASCENDING)], name="idx_feature_snapshots_action")
    await feature_snapshots.create_index([("created_at", DESCENDING)], name="idx_feature_snapshots_created")

    training_events = repository.collection(FRAUD_TRAINING_EVENTS_COLLECTION)
    await training_events.create_index([("visitor_id", ASCENDING)], name="idx_training_events_visitor")
    await training_events.create_index([("action_type", ASCENDING)], name="idx_training_events_action")
    await training_events.create_index([("outcome_label", ASCENDING)], name="idx_training_events_label")
    await training_events.create_index([("label_source", ASCENDING)], name="idx_training_events_label_source")
    await training_events.create_index([("created_at", DESCENDING)], name="idx_training_events_created")

    labels = repository.collection(FRAUD_LABELS_COLLECTION)
    await labels.create_index([("visitor_id", ASCENDING)], name="idx_fraud_labels_visitor")
    await labels.create_index([("created_at", DESCENDING)], name="idx_fraud_labels_created")

    versions = repository.collection(ML_MODEL_VERSIONS_COLLECTION)
    await versions.create_index([("status", ASCENDING)], name="idx_ml_versions_status")
    await versions.create_index([("version", ASCENDING)], name="idx_ml_versions_version")
    await versions.create_index([("created_at", DESCENDING)], name="idx_ml_versions_created")

    decisions = repository.collection(FRAUD_DECISIONS_COLLECTION)
    await decisions.create_index([("visitor_id", ASCENDING)], name="idx_fraud_decisions_visitor")
    await decisions.create_index([("action_type", ASCENDING)], name="idx_fraud_decisions_action")
    await decisions.create_index([("decision", ASCENDING)], name="idx_fraud_decisions_decision")
    await decisions.create_index([("risk_level", ASCENDING)], name="idx_fraud_decisions_risk")
    await decisions.create_index([("user_id", ASCENDING)], name="idx_fraud_decisions_user")
    await decisions.create_index([("created_at", DESCENDING)], name="idx_fraud_decisions_created")
    logger.info("Ensured fraud engine collection indexes")


def _build_decision_query(
    visitor_id: str | None = None,
    action_type: str | None = None,
    decision: str | None = None,
    risk_level: str | None = None,
    user_id: str | None = None,
    search: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if visitor_id:
        query["visitor_id"] = visitor_id
    if action_type:
        query["action_type"] = action_type
    if decision:
        query["decision"] = decision
    if risk_level:
        query["risk_level"] = risk_level
    if user_id:
        query["user_id"] = user_id
    if created_from or created_to:
        created_at: dict[str, Any] = {}
        if created_from:
            created_at["$gte"] = created_from
        if created_to:
            created_at["$lte"] = created_to
        query["created_at"] = created_at
    if search:
        search_regex = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [
            {"visitor_id": search_regex},
            {"user_id": search_regex},
            {"action_type": search_regex},
            {"decision": search_regex},
            {"risk_level": search_regex},
        ]
    return query
