from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.fraud_engine.ml_model import FraudMLModel
from app.fraud_engine.rule_engine import RuleEngine
from app.fraud_engine.synthetic_data import GRAY_SCENARIOS, generate_dataset, write_dataset
from app.fraud_engine.training_service import TrainingService
from app.fraud_engine.weak_labeler import weak_label_from_rule_score


def test_synthetic_dataset_has_required_size_and_labels(tmp_path: Path) -> None:
    csv_path = tmp_path / "synthetic.csv"
    metadata_path = tmp_path / "metadata.json"

    metadata = write_dataset(csv_path=csv_path, metadata_path=metadata_path)
    rows = generate_dataset()

    assert metadata["total_rows"] >= 12000
    assert csv_path.exists()
    assert metadata_path.exists()
    assert {row["label"] for row in rows} == {0, 1}
    assert any(row["scenario_name"] in GRAY_SCENARIOS for row in rows)


def test_same_ip_only_is_not_fraud_labeled() -> None:
    rows = generate_dataset()
    same_ip_rows = [
        row for row in rows if row["scenario_name"] == "SAME_IP_DIFFERENT_USERS"
    ]

    assert same_ip_rows
    assert all(row["label"] == 0 for row in same_ip_rows)

    weak_label = weak_label_from_rule_score(
        10,
        {
            "num_ip_addresses": 1,
            "num_cookie_ids": 1,
            "num_fingerprint_hashes": 1,
            "num_device_profile_hashes": 1,
            "identity_link_confidence_max": 10,
        },
    )
    assert weak_label["outcome_label"] is None
    assert weak_label["label_source"] == "UNKNOWN"


def test_training_from_synthetic_csv_creates_candidate_model(tmp_path: Path) -> None:
    csv_path = tmp_path / "synthetic.csv"
    metadata_path = tmp_path / "metadata.json"
    write_dataset(csv_path=csv_path, metadata_path=metadata_path)

    registry = _MemoryModelRegistry(tmp_path / "models")
    service = TrainingService(registry=registry)

    result = _run_async(
        service.train(
            synthetic_csv=str(csv_path),
            auto_activate=False,
            model_type="random_forest",
        )
    )

    assert result["success"] is True
    assert result["activated"] is False
    assert result["model_version"]["status"] == "CANDIDATE"
    assert result["model_version"]["trained_on_event_count"] >= 12000
    assert result["model_version"]["positive_label_count"] > 0
    assert result["model_version"]["negative_label_count"] > 0
    assert Path(result["model_version"]["model_path"]).exists()
    assert any(registry.versions_dir.glob("isolation_forest_*.joblib"))


def test_training_metrics_are_saved(tmp_path: Path) -> None:
    csv_path = tmp_path / "synthetic.csv"
    metadata_path = tmp_path / "metadata.json"
    write_dataset(csv_path=csv_path, metadata_path=metadata_path)

    registry = _MemoryModelRegistry(tmp_path / "models")
    service = TrainingService(registry=registry)

    result = _run_async(
        service.train(
            synthetic_csv=str(csv_path),
            auto_activate=False,
            model_type="random_forest",
        )
    )

    metrics = result["model_version"]["metrics"]
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "confusion_matrix" in metrics


def test_rule_engine_scores_and_caps() -> None:
    result = RuleEngine().evaluate(
        {
            "num_cookie_ids": 5,
            "same_fingerprint_multiple_cookies": 1,
            "sessions_last_10_min": 8,
            "has_tor_ip": 1,
            "webdriver_detected": 1,
            "headless_suspected": 1,
            "blocked_attempts": 5,
        }
    )

    assert result.rule_score == 100
    codes = {reason.code for reason in result.reasons}
    assert "SAME_FINGERPRINT_MULTIPLE_COOKIES" in codes
    assert "WEBDRIVER_DETECTED" in codes
    assert "TOR_IP" in codes


def test_missing_ml_model_is_optional_safe() -> None:
    result = FraudMLModel(registry=_MissingModelRegistry()).predict({})

    assert result.fraud_probability == 0
    assert result.anomaly_score == 0
    assert result.model_version == "none"


def _run_async(awaitable):
    import asyncio

    return asyncio.run(awaitable)


class _MemoryModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.versions_dir = root / "model_versions"
        self.active_path = root / "active_model.json"
        self.created_versions: list[dict] = []

    async def create_version(
        self,
        model_name: str,
        version: str,
        model_type: str,
        status: str,
        trained_on_event_count: int,
        positive_label_count: int,
        negative_label_count: int,
        metrics: dict,
        feature_columns: list[str],
        model_path: str,
        metadata: dict | None = None,
    ) -> dict:
        model_version = {
            "id": f"test-{len(self.created_versions) + 1}",
            "model_name": model_name,
            "version": version,
            "model_type": model_type,
            "status": status,
            "trained_on_event_count": trained_on_event_count,
            "positive_label_count": positive_label_count,
            "negative_label_count": negative_label_count,
            "metrics": metrics,
            "feature_columns": feature_columns,
            "model_path": model_path,
            "metadata": metadata or {},
        }
        self.created_versions.append(model_version)
        return model_version

    async def activate(self, model_version_id: str) -> dict:
        return {"id": model_version_id, "status": "ACTIVE"}


class _MissingModelRegistry:
    def active_config(self) -> dict:
        return {
            "fraud_classifier": None,
            "isolation_forest": None,
            "feature_columns": [],
            "version": "none",
        }

    def model_file(self, filename: str | None) -> Path | None:
        return None
