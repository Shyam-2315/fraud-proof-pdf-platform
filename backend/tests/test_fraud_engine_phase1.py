import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from pymongo import MongoClient

os.environ.setdefault("ADMIN_API_KEY", "change-me-admin-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.fraud_engine.decision_engine import FraudEngineDecisionService
from app.fraud_engine.rule_engine import RuleEngine


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8025")
MONGO_URL = os.getenv("TEST_MONGO_URL", os.getenv("MONGO_URL", "mongodb://localhost:27225"))
MONGO_DB_NAME = os.getenv("TEST_MONGO_DB_NAME", "fraud_proof_pdf")

CUSTOMER_FORBIDDEN_FIELDS = {
    "risk_score",
    "risk_level",
    "fingerprint_hash",
    "fingerprint_hashes",
    "ip_address",
    "ip_addresses",
    "user_agent",
    "user_agents",
    "cookie_id",
    "session_id",
    "session_ids",
    "local_storage_ids",
    "tracked_signals",
    "matched_signals",
}


def _payload(
    prefix: str,
    *,
    local_storage_id: str | None = None,
    session_id: str | None = None,
    fingerprint_hash: str | None = None,
    webdriver: bool = False,
) -> dict:
    return {
        "local_storage_id": local_storage_id or f"{prefix}-local",
        "session_id": session_id or f"{prefix}-session",
        "fingerprint_hash": fingerprint_hash or f"{prefix}-fingerprint",
        "device_profile_hash": f"{prefix}-device",
        "canvas_hash": f"{prefix}-canvas",
        "webgl_hash": f"{prefix}-webgl",
        "audio_hash": f"{prefix}-audio",
        "device_info": {
            "screen": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "touch_support": 0,
        },
        "automation_signals": {
            "webdriver": webdriver,
            "plugins_count": 5,
            "cookies_enabled": True,
            "local_storage_available": True,
            "session_storage_available": True,
        },
    }


def _assert_customer_safe(body: dict) -> None:
    serialized = str(body)
    for field in CUSTOMER_FORBIDDEN_FIELDS:
        assert field not in body
        assert field not in serialized


def test_same_fingerprint_with_new_cookie_uses_strong_match() -> None:
    prefix = f"phase1-fp-{uuid4()}"
    fingerprint_hash = f"{prefix}-shared-fingerprint"

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as first_client:
        first = first_client.post(
            "/api/visitor/identify",
            json=_payload(prefix, fingerprint_hash=fingerprint_hash),
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        _assert_customer_safe(first_body)

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as second_client:
        second = second_client.post(
            "/api/visitor/identify",
            json=_payload(
                f"{prefix}-new-cookie",
                local_storage_id=f"{prefix}-new-local",
                session_id=f"{prefix}-new-session",
                fingerprint_hash=fingerprint_hash,
            ),
        )
        assert second.status_code == 200, second.text
        second_body = second.json()
        _assert_customer_safe(second_body)

    assert second_body["visitor_id"] == first_body["visitor_id"]

    mongo = MongoClient(MONGO_URL)
    link = mongo[MONGO_DB_NAME].visitor_identity_links.find_one(
        {
            "source_visitor_id": first_body["visitor_id"],
            "target_visitor_id": first_body["visitor_id"],
            "link_type": "FINGERPRINT_MATCH",
            "confidence": 80,
        }
    )
    assert link is not None


def test_same_ip_only_does_not_merge_visitors() -> None:
    ip_address = "198.51.100.44"
    first_prefix = f"phase1-ip-a-{uuid4()}"
    second_prefix = f"phase1-ip-b-{uuid4()}"

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers={"X-Forwarded-For": ip_address, "User-Agent": "PDFCraftTestA"},
    ) as first_client:
        first = first_client.post("/api/visitor/identify", json=_payload(first_prefix))
        assert first.status_code == 200, first.text

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers={"X-Forwarded-For": ip_address, "User-Agent": "PDFCraftTestB"},
    ) as second_client:
        second = second_client.post("/api/visitor/identify", json=_payload(second_prefix))
        assert second.status_code == 200, second.text

    assert first.json()["visitor_id"] != second.json()["visitor_id"]


def test_rule_engine_score_is_capped_at_100() -> None:
    result = RuleEngine().evaluate(
        {
            "cookie_missing_after_seen": 1,
            "same_fingerprint_multiple_cookies": 1,
            "num_local_storage_ids": 1,
            "num_session_ids": 9,
            "sessions_last_10_min": 9,
            "ips_last_30_min": 9,
            "webdriver_detected": 1,
            "time_to_first_generate_seconds": 0.5,
            "blocked_attempts": 4,
            "many_visitors_same_ip": 9,
            "cleared_cookie_same_fingerprint": 1,
        }
    )
    assert result["rule_score"] == 100


def test_webdriver_true_increases_risk() -> None:
    result = RuleEngine().evaluate({"webdriver_detected": 1})
    assert result["rule_score"] == 40
    assert {reason["code"] for reason in result["reasons"]} == {"WEBDRIVER_DETECTED"}


def test_decision_engine_returns_require_login_for_high_risk_anonymous_visitor() -> None:
    decision = asyncio.run(
        _decide_with_features(
            {"webdriver_detected": 1, "same_fingerprint_multiple_cookies": 1},
            user=None,
        )
    )
    assert decision["risk_level"] == "HIGH"
    assert decision["decision"] == "REQUIRE_LOGIN"


def test_logged_in_user_is_not_blocked_by_anonymous_visitor_block_state() -> None:
    decision = asyncio.run(
        _decide_with_features(
            {
                "webdriver_detected": 1,
                "same_fingerprint_multiple_cookies": 1,
                "cleared_cookie_same_fingerprint": 1,
            },
            user={"_id": "user-1"},
            visitor={"_id": "visitor-1", "is_blocked": True, "free_usage_count": 2},
        )
    )
    assert decision["risk_level"] == "CRITICAL"
    assert decision["decision"] == "ALLOW_LOG"


def test_customer_identify_response_does_not_expose_internal_fields() -> None:
    prefix = f"phase1-safe-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/api/visitor/identify",
            json=_payload(prefix, webdriver=True),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body == {
            "success": True,
            "visitor_id": body["visitor_id"],
            "message": "Ready to generate PDFs.",
        }
        _assert_customer_safe(body)


async def _decide_with_features(
    features: dict,
    *,
    user: dict | None,
    visitor: dict | None = None,
) -> dict:
    service = FraudEngineDecisionService(
        repository=_MemoryDecisionRepository(),
        feature_builder=_StaticFeatureBuilder(features),
        visitor_repository=_MemoryVisitorRepository(),
        snapshot_repository=_MemorySnapshotRepository(),
        fraud_event_service=_MemoryFraudEventService(),
    )
    result = await service.decide(
        visitor=visitor or {"_id": "visitor-1", "free_usage_count": 0},
        request=None,
        action_type="PDF_GENERATE_ATTEMPT",
        user=user,
    )
    return result.as_dict()


class _StaticFeatureBuilder:
    def __init__(self, features: dict) -> None:
        self.features = features

    async def build(self, **_kwargs: object) -> dict:
        return self.features


class _MemoryDecisionRepository:
    async def create_decision(self, data: dict) -> dict:
        return data

    async def create_training_event(self, data: dict) -> dict:
        return data


class _MemorySnapshotRepository:
    async def create(self, data: dict) -> dict:
        return data


class _MemoryVisitorRepository:
    async def update_visitor(self, visitor_id: str, update_data: dict) -> dict:
        return {"_id": visitor_id, **update_data}


class _MemoryFraudEventService:
    async def create_event(self, **kwargs: object) -> dict:
        return dict(kwargs)
