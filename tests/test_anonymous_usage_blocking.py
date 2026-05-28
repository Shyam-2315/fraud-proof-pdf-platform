import asyncio
from types import SimpleNamespace

from fastapi import Request

from app.schemas.pdf import PDFGenerateRequest
from app.services.anonymous_usage_service import AnonymousUsageService
from app.services.pdf_service import PDFService


class _AnonymousUsageServiceForStatusTests(AnonymousUsageService):
    def __init__(self) -> None:
        self.settings = SimpleNamespace()
        self.repository = SimpleNamespace()

    def shared_ip_quota_enabled(self) -> bool:
        return False

    def free_usage_limit(self) -> int:
        return 2


class _AnonymousUsageServiceForPdfTest:
    def __init__(self) -> None:
        self._calls = 0

    async def get_anonymous_usage_status(self, *, request, visitor, active_window=None):
        self._calls += 1
        if self._calls == 1:
            return {
                "used": 0,
                "remaining": 2,
                "free_limit": 2,
                "free_usage_count": 0,
                "free_usage_limit": 2,
                "remaining_free_uses": 2,
                "visitor_usage_count": 0,
                "ip_usage_count": 0,
                "device_usage_count": 0,
                "fingerprint_usage_count": 0,
                "limit_reached": False,
                "fraud_blocked": False,
                "visitor_blocked": True,
                "block_reason": None,
                "is_blocked": False,
                "message": None,
                "requires_login": False,
                "active_window": None,
            }
        return {
            "used": 1,
            "remaining": 1,
            "free_limit": 2,
            "free_usage_count": 1,
            "free_usage_limit": 2,
            "remaining_free_uses": 1,
            "visitor_usage_count": 1,
            "ip_usage_count": 0,
            "device_usage_count": 0,
            "fingerprint_usage_count": 0,
            "limit_reached": False,
            "fraud_blocked": False,
            "visitor_blocked": True,
            "block_reason": None,
            "is_blocked": False,
            "message": None,
            "requires_login": False,
            "active_window": None,
        }

    async def record_anonymous_pdf_usage(
        self,
        ip_address,
        visitor_id,
        anon_id=None,
        fingerprint_hash=None,
        user_agent=None,
    ):
        return None


class _VisitorRepositoryStub:
    async def increment_free_usage(self, visitor_id: str):
        return {
            "_id": visitor_id,
            "free_usage_count": 1,
            "ip_addresses": ["127.0.0.1"],
            "session_ids": ["session-1"],
            "user_agents": ["pytest"],
            "fingerprint_hashes": ["fingerprint-1"],
            "local_storage_ids": ["local-1"],
            "device_profile_hashes": ["device-1"],
            "primary_fingerprint_hash": "fingerprint-1",
            "automation_signals": {},
        }


class _PDFRepositoryStub:
    async def create_pdf_record(self, pdf_data):
        self.pdf_data = pdf_data


class _FraudServiceStub:
    async def create_blocked_entity(self, **kwargs):
        return None

    async def create_fraud_events(self, visitor_id, events):
        return None


class _FraudEventServiceStub:
    async def create_from_request(self, **kwargs):
        return None


class _FraudDecisionServiceStub:
    async def decide(self, **kwargs):
        return {"decision": "ALLOW", "risk_score": 0, "risk_level": "LOW", "reasons": []}


class _BehaviorRepositoryStub:
    async def count_by_visitor(self, visitor_id, event_type=None, since=None):
        if event_type == "PAGE_VIEW":
            return 1
        return 0


class _BehaviorServiceStub:
    def __init__(self) -> None:
        self.repository = _BehaviorRepositoryStub()

    async def record_internal_event(self, **kwargs):
        return None


class _VisitorServiceStub:
    async def find_visitor_from_request(self, request):
        return None


class _IPIntelligenceStub:
    async def lookup(self, ip_address):
        return {"risk_score": 0, "is_datacenter": False}


class _RiskDecision:
    def as_dict(self):
        return {"decision": "ALLOW", "reasons": [], "risk_score": 0}


class _RiskEngineStub:
    def decide(self, signals):
        return _RiskDecision()


def _request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/visitor/status",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_stale_visitor_blocked_flag_with_remaining_allows_status_and_generation(monkeypatch) -> None:
    status_service = _AnonymousUsageServiceForStatusTests()
    request = _request({"X-Forwarded-For": "127.0.0.1"})
    visitor = {
        "_id": "visitor-1",
        "free_usage_count": 0,
        "is_blocked": True,
        "fraud_blocked": True,
        "block_reason": "FREE_LIMIT_REACHED",
        "automation_signals": {},
        "ip_addresses": ["127.0.0.1"],
        "session_ids": ["session-1"],
        "user_agents": ["pytest"],
        "fingerprint_hashes": ["fingerprint-1"],
        "local_storage_ids": ["local-1"],
        "device_profile_hashes": ["device-1"],
        "primary_fingerprint_hash": "fingerprint-1",
    }

    usage_status = asyncio.run(
        status_service.get_anonymous_usage_status(request=request, visitor=visitor)
    )

    assert usage_status["used"] == 0
    assert usage_status["remaining"] == 2
    assert usage_status["limit_reached"] is False
    assert usage_status["fraud_blocked"] is False
    assert usage_status["is_blocked"] is False
    assert usage_status["block_reason"] is None

    monkeypatch.setattr(
        "app.services.pdf_service.generate_simple_pdf",
        lambda title, content, output_dir: ("generated.pdf", "/tmp/generated.pdf"),
    )
    pdf_service = PDFService(
        visitor_repository=_VisitorRepositoryStub(),
        pdf_repository=_PDFRepositoryStub(),
        fraud_service=_FraudServiceStub(),
        fraud_event_service=_FraudEventServiceStub(),
        fraud_decision_service=_FraudDecisionServiceStub(),
        behavior_service=_BehaviorServiceStub(),
        visitor_service=_VisitorServiceStub(),
        anonymous_usage_service=_AnonymousUsageServiceForPdfTest(),
        ip_intelligence=_IPIntelligenceStub(),
        risk_engine=_RiskEngineStub(),
    )

    response = asyncio.run(
        pdf_service._generate_pdf_for_anonymous_visitor(
            request=_request({"user-agent": "pytest", "X-Forwarded-For": "127.0.0.1"}),
            payload=PDFGenerateRequest(title="Test PDF", content="Body"),
            visitor=visitor,
        )
    )

    assert response.success is True
    assert response.used == 1
    assert response.remaining == 1
    assert response.requires_login is False


def test_remaining_zero_is_limit_blocked() -> None:
    service = _AnonymousUsageServiceForStatusTests()
    request = _request({"X-Forwarded-For": "127.0.0.1"})
    visitor = {
        "_id": "visitor-2",
        "free_usage_count": 2,
        "is_blocked": True,
        "fraud_blocked": False,
        "block_reason": "FREE_LIMIT_REACHED",
    }

    usage_status = asyncio.run(
        service.get_anonymous_usage_status(request=request, visitor=visitor)
    )

    assert usage_status["remaining"] == 0
    assert usage_status["limit_reached"] is True
    assert usage_status["fraud_blocked"] is False
    assert usage_status["is_blocked"] is True
    assert usage_status["block_reason"] == "FREE_LIMIT_REACHED"


def test_explicit_fraud_blocked_stays_blocked() -> None:
    service = _AnonymousUsageServiceForStatusTests()
    request = _request({"X-Forwarded-For": "127.0.0.1"})
    visitor = {
        "_id": "visitor-3",
        "free_usage_count": 0,
        "is_blocked": True,
        "fraud_blocked": True,
        "block_reason": "HIGH_RISK_FINGERPRINT",
    }

    usage_status = asyncio.run(
        service.get_anonymous_usage_status(request=request, visitor=visitor)
    )

    assert usage_status["remaining"] == 2
    assert usage_status["limit_reached"] is False
    assert usage_status["fraud_blocked"] is True
    assert usage_status["is_blocked"] is True
    assert usage_status["block_reason"] == "HIGH_RISK_FINGERPRINT"
