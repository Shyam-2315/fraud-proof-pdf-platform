import asyncio
from copy import deepcopy

from starlette.requests import Request

import app.services.visitor_resolution as visitor_resolution_module
from app.models.fraud_event import FraudEventType
from app.services.visitor_resolution import VisitorResolutionService


class _FakeVisitorRepository:
    def __init__(self, visitor: dict | None) -> None:
        self.visitor = deepcopy(visitor)
        self.updated_visitor = None

    async def find_by_cookie_id(self, cookie_id: str | None):
        if self.visitor and cookie_id and cookie_id in self.visitor.get("cookie_ids", []):
            return deepcopy(self.visitor)
        return None

    async def find_by_local_storage_id(self, local_storage_id: str | None):
        if self.visitor and local_storage_id and local_storage_id in self.visitor.get("local_storage_ids", []):
            return deepcopy(self.visitor)
        return None

    async def find_by_fingerprint_hash(self, fingerprint_hash: str | None):
        if self.visitor and fingerprint_hash and fingerprint_hash in self.visitor.get("fingerprint_hashes", []):
            return deepcopy(self.visitor)
        return None

    async def find_by_session_id(self, session_id: str | None):
        if self.visitor and session_id and session_id in self.visitor.get("session_ids", []):
            return deepcopy(self.visitor)
        return None

    async def find_by_device_profile_hash(self, device_profile_hash: str | None):
        if self.visitor and device_profile_hash and device_profile_hash in self.visitor.get("device_profile_hashes", []):
            return deepcopy(self.visitor)
        return None

    async def update_visitor(self, visitor_id: str, update_data: dict):
        assert self.visitor is not None
        assert self.visitor["_id"] == visitor_id
        self.visitor = {**self.visitor, **deepcopy(update_data)}
        self.updated_visitor = deepcopy(self.visitor)
        return deepcopy(self.visitor)


class _FakeFraudEventService:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def create_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


def _request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/visitor/status",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "https",
    }
    return Request(scope)


def _run_resolution(
    visitor: dict,
    headers: dict[str, str],
    ip_address: str,
) -> tuple[dict | None, _FakeVisitorRepository, _FakeFraudEventService]:
    repository = _FakeVisitorRepository(visitor)
    fraud_event_service = _FakeFraudEventService()
    service = VisitorResolutionService(
        repository=repository,
        fraud_event_service=fraud_event_service,
    )
    request = _request(headers)

    async def _anonymous_user(_request: Request):
        return None

    original_auth = visitor_resolution_module.get_current_user_optional
    original_ip_details = visitor_resolution_module.get_client_ip_details
    visitor_resolution_module.get_current_user_optional = _anonymous_user
    visitor_resolution_module.get_client_ip_details = lambda _request: {
        "resolved_client_ip": ip_address,
        "proxy_hop_count": 0,
    }
    try:
        resolved_visitor, _ = asyncio.run(service.resolve(request))
    finally:
        visitor_resolution_module.get_current_user_optional = original_auth
        visitor_resolution_module.get_client_ip_details = original_ip_details

    return resolved_visitor, repository, fraud_event_service


def test_cookie_missing_but_x_anon_id_reuses_existing_visitor() -> None:
    visitor = {
        "_id": "visitor-1",
        "cookie_ids": ["anon-existing"],
        "local_storage_ids": ["visitor-local-1"],
        "session_ids": ["session-1"],
        "fingerprint_hashes": ["fingerprint-1"],
        "ip_addresses": ["198.51.100.10"],
        "user_agents": ["PDFCraftTest/1.0"],
        "free_usage_count": 2,
    }

    resolved_visitor, repository, _ = _run_resolution(
        visitor,
        headers={
            "X-Anon-Id": "anon-existing",
            "X-Visitor-Id": "visitor-local-1",
            "X-Session-Id": "session-2",
            "X-Device-Fingerprint": "fingerprint-1",
            "User-Agent": "PDFCraftTest/1.0",
        },
        ip_address="198.51.100.10",
    )

    assert resolved_visitor is not None
    assert resolved_visitor["_id"] == "visitor-1"
    assert repository.updated_visitor is not None
    assert repository.updated_visitor["free_usage_count"] == 2
    assert "session-2" in repository.updated_visitor["session_ids"]


def test_cookie_missing_but_fingerprint_reuses_existing_visitor() -> None:
    visitor = {
        "_id": "visitor-2",
        "cookie_ids": ["anon-2"],
        "local_storage_ids": ["visitor-local-2"],
        "session_ids": ["session-2"],
        "fingerprint_hashes": ["fingerprint-2"],
        "ip_addresses": ["198.51.100.20"],
        "user_agents": ["PDFCraftTest/2.0"],
        "free_usage_count": 1,
    }

    resolved_visitor, repository, _ = _run_resolution(
        visitor,
        headers={
            "X-Visitor-Id": "brand-new-local",
            "X-Session-Id": "brand-new-session",
            "X-Device-Fingerprint": "fingerprint-2",
            "User-Agent": "PDFCraftTest/2.0",
        },
        ip_address="198.51.100.20",
    )

    assert resolved_visitor is not None
    assert resolved_visitor["_id"] == "visitor-2"
    assert repository.updated_visitor is not None
    assert repository.updated_visitor["free_usage_count"] == 1
    assert "fingerprint-2" in repository.updated_visitor["fingerprint_hashes"]


def test_same_visitor_ip_change_does_not_reset_usage_and_records_admin_event() -> None:
    visitor = {
        "_id": "visitor-3",
        "cookie_ids": ["anon-3"],
        "local_storage_ids": ["visitor-local-3"],
        "session_ids": ["session-3"],
        "fingerprint_hashes": ["fingerprint-3"],
        "ip_addresses": ["198.51.100.30"],
        "user_agents": ["PDFCraftTest/3.0"],
        "free_usage_count": 2,
        "risk_score": 0,
        "risk_level": "LOW",
    }

    resolved_visitor, repository, fraud_event_service = _run_resolution(
        visitor,
        headers={
            "X-Visitor-Id": "visitor-local-3",
            "X-Session-Id": "session-3",
            "X-Device-Fingerprint": "fingerprint-3",
            "User-Agent": "PDFCraftTest/3.0",
        },
        ip_address="198.51.100.31",
    )

    assert resolved_visitor is not None
    assert repository.updated_visitor is not None
    assert repository.updated_visitor["free_usage_count"] == 2
    assert repository.updated_visitor["ip_addresses"] == ["198.51.100.30", "198.51.100.31"]
    assert repository.updated_visitor["ip_change_history"][-1]["event_type"] == FraudEventType.DYNAMIC_IP_CHANGE.value
    assert fraud_event_service.events[-1]["event_type"] == FraudEventType.DYNAMIC_IP_CHANGE.value
