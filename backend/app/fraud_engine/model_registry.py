import json
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.fraud_engine.schemas import FEATURE_COLUMNS
from app.repositories.fraud_engine_repository import FraudEngineRepository
from app.utils.security import generate_uuid, utc_now


class ModelRegistry:
    def __init__(self, repository: FraudEngineRepository | None = None) -> None:
        self.repository = repository or FraudEngineRepository()
        self.root = Path("models/fraud")
        self.versions_dir = self.root / "model_versions"
        self.active_path = self.root / "active_model.json"

    def active_config(self) -> dict[str, Any]:
        if not self.active_path.exists():
            return {
                "fraud_classifier": None,
                "isolation_forest": None,
                "feature_columns": FEATURE_COLUMNS,
                "version": "none",
            }
        try:
            return json.loads(self.active_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "fraud_classifier": None,
                "isolation_forest": None,
                "feature_columns": FEATURE_COLUMNS,
                "version": "none",
            }

    def model_file(self, filename: str | None) -> Path | None:
        if not filename:
            return None
        return self.versions_dir / filename

    async def create_version(
        self,
        model_name: str,
        version: str,
        model_type: str,
        status: str,
        trained_on_event_count: int,
        positive_label_count: int,
        negative_label_count: int,
        metrics: dict[str, Any],
        feature_columns: list[str],
        model_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        model_version_id = generate_uuid()
        return await self.repository.create_model_version(
            {
                "_id": model_version_id,
                "id": model_version_id,
                "model_name": model_name,
                "version": version,
                "model_type": model_type,
                "status": status,
                "training_started_at": metadata.get("training_started_at") if metadata else None,
                "training_completed_at": utc_now(),
                "trained_on_event_count": trained_on_event_count,
                "positive_label_count": positive_label_count,
                "negative_label_count": negative_label_count,
                "metrics": metrics,
                "feature_columns": feature_columns,
                "model_path": model_path,
                "metadata": metadata or {},
                "created_at": utc_now(),
            }
        )

    async def list_versions(self) -> list[dict[str, Any]]:
        return await self.repository.list_model_versions(limit=100)

    async def activate(self, model_version_id: str) -> dict[str, Any] | None:
        version = await self.repository.get_model_version(model_version_id)
        if version is None:
            return None
        await self.repository.archive_active_models()
        activated = await self.repository.update_model_status(model_version_id, "ACTIVE")
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.root.mkdir(parents=True, exist_ok=True)
        active_config = {
            "fraud_classifier": Path(str(version.get("model_path", ""))).name,
            "isolation_forest": f"isolation_forest_{version.get('version')}.joblib",
            "feature_columns": version.get("feature_columns") or FEATURE_COLUMNS,
            "version": version.get("version"),
            "model_version_id": model_version_id,
        }
        self.active_path.write_text(json.dumps(active_config, indent=2), encoding="utf-8")
        return activated

    async def reject(self, model_version_id: str) -> dict[str, Any] | None:
        return await self.repository.update_model_status(model_version_id, "REJECTED")
