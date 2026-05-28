from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.fraud_engine.model_registry import ModelRegistry
from app.fraud_engine.schemas import FEATURE_COLUMNS
from app.repositories.fraud_engine_repository import FraudEngineRepository
from app.utils.security import utc_now


class TrainingService:
    """
    Fraud-detection component used to score, classify, or train signals.
    """
    def __init__(
        self,
        repository: FraudEngineRepository | None = None,
        registry: ModelRegistry | None = None,
    ) -> None:
        """
        Initialize the fraud-detection component and its collaborators.
        
        Args:
            repository: The repository value used by this operation.
            registry: The registry value used by this operation.
        
        Returns:
            None.
        """
        self.repository = repository or FraudEngineRepository()
        self.registry = registry or ModelRegistry(repository=self.repository)

    async def train(
        self,
        synthetic_csv: str | None = None,
        demo: bool = False,
        auto_activate: bool = False,
        min_confidence: float = 0.70,
        model_type: str = "random_forest",
    ) -> dict[str, Any]:
        """
        Train for the requested operation.
        
        Args:
            synthetic_csv: The synthetic csv value used by this operation.
            demo: The demo value used by this operation.
            auto_activate: The auto activate value used by this operation.
            min_confidence: Minimum confidence value allowed for the operation.
            model_type: The model type value used by this operation.
        
        Returns:
            Operation result represented as `dict[str, Any]`.
        """
        started_at = utc_now()
        dataset = await self._load_dataset(
            synthetic_csv=synthetic_csv,
            demo=demo,
            min_confidence=min_confidence,
        )
        if not dataset["success"]:
            return dataset
        df = dataset["dataframe"]
        is_synthetic = bool(dataset["synthetic"])
        positives = int((df["label"] == 1).sum())
        negatives = int((df["label"] == 0).sum())
        if not is_synthetic and (len(df) < 100 or positives < 20 or negatives < 20):
            return {
                "success": False,
                "reason": "Not enough labeled data for safe retraining.",
                "event_count": len(df),
                "positive_label_count": positives,
                "negative_label_count": negatives,
            }

        x = df[FEATURE_COLUMNS].fillna(0).astype(float)
        y = df["label"].astype(int)
        stratify = y if positives >= 2 and negatives >= 2 else None
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=0.25,
            random_state=2525,
            stratify=stratify,
        )
        if model_type == "logistic_regression":
            classifier = LogisticRegression(max_iter=1000, class_weight="balanced")
        else:
            classifier = RandomForestClassifier(
                n_estimators=140,
                max_depth=12,
                min_samples_leaf=4,
                random_state=2525,
                class_weight="balanced",
                n_jobs=-1,
            )
        classifier.fit(x_train, y_train)
        isolation = IsolationForest(
            n_estimators=100,
            contamination=0.08,
            random_state=2525,
            n_jobs=-1,
        )
        isolation.fit(x_train)
        predictions = classifier.predict(x_test)
        probabilities = (
            classifier.predict_proba(x_test)[:, 1]
            if hasattr(classifier, "predict_proba")
            else predictions
        )
        metrics = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision": float(precision_score(y_test, predictions, zero_division=0)),
            "recall": float(recall_score(y_test, predictions, zero_division=0)),
            "f1_score": float(f1_score(y_test, predictions, zero_division=0)),
            "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        }
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities))
        except ValueError:
            metrics["roc_auc"] = None

        version = f"v{utc_now().strftime('%Y%m%d%H%M%S')}"
        self.registry.versions_dir.mkdir(parents=True, exist_ok=True)
        classifier_filename = f"fraud_classifier_{version}.joblib"
        isolation_filename = f"isolation_forest_{version}.joblib"
        classifier_path = self.registry.versions_dir / classifier_filename
        isolation_path = self.registry.versions_dir / isolation_filename
        joblib.dump(classifier, classifier_path)
        joblib.dump(isolation, isolation_path)

        can_activate = _passes_activation(metrics) and (
            (not is_synthetic and len(df) >= 100 and positives >= 20 and negatives >= 20)
            or (is_synthetic and auto_activate)
        )
        model_version = await self.registry.create_version(
            model_name="pdfcraft_fraud_classifier",
            version=version,
            model_type=model_type,
            status="CANDIDATE",
            trained_on_event_count=len(df),
            positive_label_count=positives,
            negative_label_count=negatives,
            metrics=metrics,
            feature_columns=FEATURE_COLUMNS,
            model_path=str(classifier_path),
            metadata={
                "synthetic": is_synthetic,
                "source": dataset["source"],
                "training_started_at": started_at,
                "isolation_forest_path": str(isolation_path),
            },
        )
        activated = False
        if can_activate:
            await self.registry.activate(model_version["id"])
            activated = True
        return {
            "success": True,
            "model_version": model_version,
            "metrics": metrics,
            "activated": activated,
            "activation_allowed": can_activate,
            "synthetic": is_synthetic,
        }

    async def _load_dataset(
        self,
        synthetic_csv: str | None,
        demo: bool,
        min_confidence: float,
    ) -> dict[str, Any]:
        """
        Load Dataset for the requested operation.
        
        Args:
            synthetic_csv: The synthetic csv value used by this operation.
            demo: The demo value used by this operation.
            min_confidence: Minimum confidence value allowed for the operation.
        
        Returns:
            Operation result represented as `dict[str, Any]`.
        """
        if synthetic_csv or demo:
            path = Path(synthetic_csv or "data/synthetic_fraud_dataset.csv")
            if not path.exists():
                return {"success": False, "reason": f"Synthetic CSV not found: {path}"}
            df = pd.read_csv(path)
            df = _normalize_dataframe(df)
            return {
                "success": True,
                "dataframe": df,
                "synthetic": True,
                "source": str(path),
            }

        events = await self.repository.list_training_events(limit=100000)
        rows = []
        labels = {label["visitor_id"]: label for label in await self.repository.list_labels()}
        for event in events:
            label_doc = labels.get(event.get("visitor_id"))
            label = event.get("outcome_label")
            confidence = float(event.get("label_confidence", 0.0) or 0.0)
            if label_doc is not None:
                label = int(label_doc["label"])
                confidence = 1.0
            if label is None or confidence < min_confidence:
                continue
            row = {column: event.get("features", {}).get(column, 0) for column in FEATURE_COLUMNS}
            row["label"] = int(label)
            rows.append(row)
        if not rows:
            return {"success": False, "reason": "Not enough labeled data for safe retraining."}
        return {
            "success": True,
            "dataframe": _normalize_dataframe(pd.DataFrame(rows)),
            "synthetic": False,
            "source": "fraud_training_events",
        }


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize Dataframe for the requested operation.
    
    Args:
        df: The df value used by this operation.
    
    Returns:
        Operation result represented as `pd.DataFrame`.
    """
    for column in FEATURE_COLUMNS:
        if column not in df.columns:
            df[column] = 0
    if "label" not in df.columns:
        df["label"] = 0
    return df[FEATURE_COLUMNS + ["label"]].fillna(0)


def _passes_activation(metrics: dict[str, Any]) -> bool:
    """
    Passes Activation for the requested operation.
    
    Args:
        metrics: The metrics value used by this operation.
    
    Returns:
        Operation result represented as `bool`.
    """
    return (
        float(metrics.get("f1_score") or 0) >= 0.70
        and float(metrics.get("precision") or 0) >= 0.65
        and float(metrics.get("recall") or 0) >= 0.60
    )
