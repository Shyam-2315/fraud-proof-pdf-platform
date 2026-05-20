import logging
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
    def collection(self, name: str) -> AsyncIOMotorCollection:
        return get_database()[name]

    async def create_feature_snapshot(self, data: dict[str, Any]) -> dict[str, Any]:
        await self.collection(FRAUD_FEATURE_SNAPSHOTS_COLLECTION).insert_one(data)
        return data

    async def list_feature_snapshots_by_visitor(
        self,
        visitor_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cursor = (
            self.collection(FRAUD_FEATURE_SNAPSHOTS_COLLECTION)
            .find({"visitor_id": visitor_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def create_training_event(self, data: dict[str, Any]) -> dict[str, Any]:
        await self.collection(FRAUD_TRAINING_EVENTS_COLLECTION).insert_one(data)
        return data

    async def count_training_events(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.collection(FRAUD_TRAINING_EVENTS_COLLECTION).count_documents(
            filter_query or {}
        )

    async def list_training_events(
        self,
        filter_query: dict[str, Any] | None = None,
        limit: int = 100000,
    ) -> list[dict[str, Any]]:
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
        await self.collection(FRAUD_LABELS_COLLECTION).insert_one(data)
        return data

    async def latest_label_for_visitor(self, visitor_id: str) -> dict[str, Any] | None:
        return await self.collection(FRAUD_LABELS_COLLECTION).find_one(
            {"visitor_id": visitor_id},
            sort=[("created_at", DESCENDING)],
        )

    async def list_labels(self, limit: int = 100000) -> list[dict[str, Any]]:
        cursor = (
            self.collection(FRAUD_LABELS_COLLECTION)
            .find({})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def create_model_version(self, data: dict[str, Any]) -> dict[str, Any]:
        await self.collection(ML_MODEL_VERSIONS_COLLECTION).insert_one(data)
        return data

    async def list_model_versions(self, limit: int = 100) -> list[dict[str, Any]]:
        cursor = (
            self.collection(ML_MODEL_VERSIONS_COLLECTION)
            .find({})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_model_version(self, model_version_id: str) -> dict[str, Any] | None:
        return await self.collection(ML_MODEL_VERSIONS_COLLECTION).find_one(
            {"_id": model_version_id}
        )

    async def update_model_status(
        self,
        model_version_id: str,
        status: str,
    ) -> dict[str, Any] | None:
        return await self.collection(ML_MODEL_VERSIONS_COLLECTION).find_one_and_update(
            {"_id": model_version_id},
            {"$set": {"status": status}},
            return_document=ReturnDocument.AFTER,
        )

    async def archive_active_models(self) -> int:
        result = await self.collection(ML_MODEL_VERSIONS_COLLECTION).update_many(
            {"status": "ACTIVE"},
            {"$set": {"status": "ARCHIVED"}},
        )
        return int(result.modified_count)

    async def create_decision(self, data: dict[str, Any]) -> dict[str, Any]:
        await self.collection(FRAUD_DECISIONS_COLLECTION).insert_one(data)
        return data

    async def list_decisions_by_visitor(
        self,
        visitor_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
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
        visitor_id: str | None = None,
        action_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if visitor_id:
            query["visitor_id"] = visitor_id
        if action_type:
            query["action_type"] = action_type
        cursor = (
            self.collection(FRAUD_DECISIONS_COLLECTION)
            .find(query)
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count_decisions(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.collection(FRAUD_DECISIONS_COLLECTION).count_documents(
            filter_query or {}
        )


async def ensure_fraud_engine_indexes() -> None:
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
    await decisions.create_index([("created_at", DESCENDING)], name="idx_fraud_decisions_created")
    logger.info("Ensured fraud engine collection indexes")
