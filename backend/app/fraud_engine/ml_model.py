import logging
from typing import Any

import joblib
import numpy as np

from app.fraud_engine.model_registry import ModelRegistry
from app.fraud_engine.schemas import FEATURE_COLUMNS, MLResult

logger = logging.getLogger(__name__)


class FraudMLModel:
    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry()

    def predict(self, features: dict[str, Any]) -> MLResult:
        config = self.registry.active_config()
        classifier_path = self.registry.model_file(config.get("fraud_classifier"))
        isolation_path = self.registry.model_file(config.get("isolation_forest"))
        if classifier_path is None or not classifier_path.exists():
            logger.warning("ML model unavailable; using rule engine fallback")
            return MLResult()

        columns = config.get("feature_columns") or FEATURE_COLUMNS
        vector = np.array([[float(features.get(column, 0) or 0) for column in columns]])
        fraud_probability = 0.0
        anomaly_score = 0.0
        try:
            classifier = joblib.load(classifier_path)
            if hasattr(classifier, "predict_proba"):
                fraud_probability = float(classifier.predict_proba(vector)[0][1])
            else:
                fraud_probability = float(classifier.predict(vector)[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("ML model unavailable; using rule engine fallback error=%s", exc)
            return MLResult()

        if isolation_path is not None and isolation_path.exists():
            try:
                isolation = joblib.load(isolation_path)
                raw_score = float(-isolation.score_samples(vector)[0])
                anomaly_score = max(0.0, min(raw_score / 0.75, 1.0))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Isolation model unavailable; anomaly score disabled error=%s", exc)

        return MLResult(
            fraud_probability=max(0.0, min(fraud_probability, 1.0)),
            anomaly_score=max(0.0, min(anomaly_score, 1.0)),
            model_version=str(config.get("version") or "none"),
        )
