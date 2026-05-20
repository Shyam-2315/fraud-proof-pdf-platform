from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.fraud_engine.ml_model import FraudMLModel
from app.fraud_engine.rule_engine import RuleEngine
from app.fraud_engine.synthetic_data import GRAY_SCENARIOS, generate_dataset, write_dataset
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
    same_ip_rows = [row for row in rows if row["scenario_name"] == "SAME_IP_DIFFERENT_USERS"]
    assert same_ip_rows
    assert all(row["label"] == 0 for row in same_ip_rows)


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


def test_same_ip_alone_does_not_create_fraud_label() -> None:
    label = weak_label_from_rule_score(
        10,
        {
            "num_ip_addresses": 1,
            "num_cookie_ids": 1,
            "num_fingerprint_hashes": 1,
            "num_device_profile_hashes": 1,
            "identity_link_confidence_max": 10,
        },
    )
    assert label["outcome_label"] is None
    assert label["label_source"] == "UNKNOWN"


def test_missing_ml_model_is_optional_safe() -> None:
    result = FraudMLModel().predict({})
    assert result.fraud_probability == 0
    assert result.anomaly_score == 0
    assert result.model_version == "none"
