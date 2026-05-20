import csv
import json
import random
from pathlib import Path
from typing import Any

from app.fraud_engine.schemas import FEATURE_COLUMNS

NORMAL_SCENARIOS = [
    "NORMAL_SINGLE_PDF",
    "NORMAL_TWO_PDFS",
    "NORMAL_LOGIN_AFTER_LIMIT",
    "NORMAL_SHARED_IP_DIFFERENT_DEVICE",
    "NORMAL_SLOW_USAGE",
]
FRAUD_SCENARIOS = [
    "COOKIE_CLEAR_SAME_FINGERPRINT",
    "MANY_COOKIES_SAME_DEVICE",
    "MANY_SESSIONS_FAST",
    "RAPID_GENERATION_BOT",
    "VPN_IP_SWITCHING",
    "DATACENTER_PROXY_USAGE",
    "TOR_USAGE",
    "API_ONLY_GENERATION",
    "REPEATED_BLOCKED_ATTEMPTS",
    "ACCOUNT_FARMING_SAME_DEVICE",
    "SAME_CONTENT_REPEATED",
    "COOKIE_AND_LOCAL_STORAGE_RESET_BUT_SAME_DEVICE_PROFILE",
]
GRAY_SCENARIOS = [
    "SAME_IP_DIFFERENT_USERS",
    "MOBILE_NETWORK_IP_CHANGE",
    "NORMAL_USER_MULTIPLE_SESSIONS",
    "COOKIE_BLOCKED_BUT_LOGIN_NORMAL",
    "TRAVEL_OR_NETWORK_CHANGE",
]

EXTRA_COLUMNS = ["scenario_name", "label", "label_confidence", "source"]
DATASET_COLUMNS = FEATURE_COLUMNS + EXTRA_COLUMNS


def generate_dataset(
    normal_count: int = 5000,
    fraud_count: int = 5000,
    gray_count: int = 2000,
    seed: int = 2525,
) -> list[dict[str, Any]]:
    random.seed(seed)
    rows: list[dict[str, Any]] = []
    for _ in range(normal_count):
        scenario = random.choice(NORMAL_SCENARIOS)
        rows.append(_row_for_scenario(scenario, label=0, confidence=0.92))
    for _ in range(fraud_count):
        scenario = random.choice(FRAUD_SCENARIOS)
        rows.append(_row_for_scenario(scenario, label=1, confidence=0.92))
    for _ in range(gray_count):
        scenario = random.choice(GRAY_SCENARIOS)
        label = 0 if scenario in {"SAME_IP_DIFFERENT_USERS", "COOKIE_BLOCKED_BUT_LOGIN_NORMAL"} else random.choice([0, 1])
        rows.append(_row_for_scenario(scenario, label=label, confidence=0.55))
    random.shuffle(rows)
    return rows


def write_dataset(
    csv_path: str | Path = "data/synthetic_fraud_dataset.csv",
    metadata_path: str | Path = "data/synthetic_fraud_dataset_metadata.json",
) -> dict[str, Any]:
    rows = generate_dataset()
    csv_path = Path(csv_path)
    metadata_path = Path(metadata_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=DATASET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "total_rows": len(rows),
        "normal_examples": sum(1 for row in rows if row["label"] == 0 and row["scenario_name"] in NORMAL_SCENARIOS),
        "fraud_examples": sum(1 for row in rows if row["label"] == 1 and row["scenario_name"] in FRAUD_SCENARIOS),
        "gray_zone_examples": sum(1 for row in rows if row["scenario_name"] in GRAY_SCENARIOS),
        "scenarios": {
            "normal": NORMAL_SCENARIOS,
            "fraud": FRAUD_SCENARIOS,
            "gray_zone": GRAY_SCENARIOS,
        },
        "same_ip_only_rule": "Same IP alone is gray-zone/normal, not fraud-labeled.",
        "source": "SYNTHETIC",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def _base(label: int, scenario: str, confidence: float) -> dict[str, Any]:
    row = {column: 0 for column in FEATURE_COLUMNS}
    row.update(
        {
            "num_cookie_ids": 1,
            "num_local_storage_ids": 1,
            "num_session_ids": 1,
            "num_fingerprint_hashes": 1,
            "num_device_profile_hashes": 1,
            "num_canvas_hashes": 1,
            "num_webgl_hashes": 1,
            "num_ip_addresses": 1,
            "num_user_agents": 1,
            "plugins_count": random.randint(3, 8),
            "time_to_first_generate_seconds": random.randint(20, 900),
            "avg_time_between_generations": random.randint(120, 3600),
            "page_views_before_generate": random.randint(1, 4),
            "generate_clicks_before_success": random.randint(1, 2),
            "scenario_name": scenario,
            "label": label,
            "label_confidence": confidence,
            "source": "SYNTHETIC",
        }
    )
    return row


def _row_for_scenario(scenario: str, label: int, confidence: float) -> dict[str, Any]:
    row = _base(label, scenario, confidence)
    if scenario == "NORMAL_TWO_PDFS":
        row["pdf_attempts_last_10_min"] = random.randint(1, 2)
    elif scenario == "NORMAL_LOGIN_AFTER_LIMIT":
        row["account_created_after_free_limit"] = 1
    elif scenario == "NORMAL_SHARED_IP_DIFFERENT_DEVICE":
        row["many_visitors_same_ip"] = random.randint(2, 8)
        row["identity_link_confidence_max"] = 10
    elif scenario == "NORMAL_SLOW_USAGE":
        row["avg_time_between_generations"] = random.randint(86400, 604800)
    elif scenario == "COOKIE_CLEAR_SAME_FINGERPRINT":
        row["num_cookie_ids"] = random.randint(2, 4)
        row["same_fingerprint_multiple_cookies"] = 1
        row["cleared_cookie_same_fingerprint"] = 1
        row["identity_link_confidence_max"] = 80
    elif scenario == "MANY_COOKIES_SAME_DEVICE":
        row["num_cookie_ids"] = random.randint(4, 9)
        row["same_fingerprint_multiple_cookies"] = 1
        row["identity_link_confidence_max"] = 80
    elif scenario == "MANY_SESSIONS_FAST":
        row["num_session_ids"] = random.randint(5, 12)
        row["sessions_last_10_min"] = random.randint(4, 10)
        row["time_to_first_generate_seconds"] = random.uniform(0.2, 1.8)
    elif scenario == "RAPID_GENERATION_BOT":
        row["webdriver_detected"] = 1
        row["headless_suspected"] = 1
        row["plugins_count"] = 0
        row["time_to_first_generate_seconds"] = random.uniform(0.1, 1.5)
        row["pdf_attempts_last_10_min"] = random.randint(6, 20)
    elif scenario == "VPN_IP_SWITCHING":
        row["has_vpn_ip"] = 1
        row["num_ip_addresses"] = random.randint(4, 10)
        row["ips_last_30_min"] = random.randint(4, 8)
        row["risky_ip_score"] = random.randint(60, 85)
    elif scenario == "DATACENTER_PROXY_USAGE":
        row["has_proxy_ip"] = 1
        row["has_datacenter_ip"] = 1
        row["risky_ip_score"] = random.randint(65, 90)
    elif scenario == "TOR_USAGE":
        row["has_tor_ip"] = 1
        row["risky_ip_score"] = random.randint(85, 100)
    elif scenario == "API_ONLY_GENERATION":
        row["api_only_usage_pattern"] = 1
        row["page_views_before_generate"] = 0
        row["generate_clicks_before_success"] = 0
    elif scenario == "REPEATED_BLOCKED_ATTEMPTS":
        row["blocked_attempts"] = random.randint(2, 8)
        row["repeated_blocked_attempts"] = row["blocked_attempts"] - 1
    elif scenario == "ACCOUNT_FARMING_SAME_DEVICE":
        row["accounts_same_device"] = random.randint(4, 20)
        row["accounts_same_ip"] = random.randint(4, 20)
    elif scenario == "SAME_CONTENT_REPEATED":
        row["same_content_repeated_count"] = random.randint(3, 12)
    elif scenario == "COOKIE_AND_LOCAL_STORAGE_RESET_BUT_SAME_DEVICE_PROFILE":
        row["num_cookie_ids"] = random.randint(2, 6)
        row["num_local_storage_ids"] = random.randint(2, 5)
        row["identity_link_confidence_max"] = 70
    elif scenario == "SAME_IP_DIFFERENT_USERS":
        row["label"] = 0
        row["label_confidence"] = 0.70
        row["many_visitors_same_ip"] = random.randint(2, 20)
        row["identity_link_confidence_max"] = 10
    elif scenario == "MOBILE_NETWORK_IP_CHANGE":
        row["num_ip_addresses"] = random.randint(2, 4)
        row["ips_last_30_min"] = random.randint(1, 3)
    elif scenario == "NORMAL_USER_MULTIPLE_SESSIONS":
        row["num_session_ids"] = random.randint(2, 4)
        row["sessions_last_10_min"] = random.randint(1, 3)
    elif scenario == "COOKIE_BLOCKED_BUT_LOGIN_NORMAL":
        row["label"] = 0
        row["account_created_after_free_limit"] = 1
    elif scenario == "TRAVEL_OR_NETWORK_CHANGE":
        row["num_ip_addresses"] = random.randint(2, 3)
        row["avg_time_between_generations"] = random.randint(86400, 259200)
    return row
