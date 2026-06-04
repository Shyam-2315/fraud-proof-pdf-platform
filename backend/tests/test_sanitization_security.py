from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.middleware import _build_content_security_policy
from app.schemas.auth import UserRegisterRequest
from app.schemas.pdf import PDFGenerateRequest
from app.services.admin_monitoring_service import _build_request_log_item
from app.services.fraud_event_service import build_fraud_event_item
from app.utils.pdf_generator import generate_simple_pdf
from app.utils.sanitization import sanitize_log_value, sanitize_mapping
from starlette.requests import Request


def test_pdf_title_with_script_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PDFGenerateRequest(title='<script>alert("xss")</script>', content="Safe content")


def test_pdf_content_with_event_handler_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PDFGenerateRequest(title="Quarterly report", content='<img src=x onerror=alert("xss")>')


def test_full_name_with_script_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        UserRegisterRequest(
            email="user@example.com",
            full_name='<svg onload=alert("xss")>',
            password="StrongPassword123",
        )


def test_request_logs_sanitize_dangerous_values() -> None:
    item = _build_request_log_item(
        {
            "request_id": '"><script>alert(1)</script>',
            "method": "GET",
            "path": "/api/pdf/<img src=x onerror=alert(1)>",
            "status_code": 403,
            "duration_ms": 12.4,
            "client_ip": '<svg onload=alert(1)>',
            "block_reason": "javascript:alert(1)",
            "created_at": None,
        }
    )

    assert item.request_id == '">alert(1)'
    assert item.path == "/api/pdf/"
    assert item.client_ip == ""
    assert item.block_reason == "javascript:alert(1)"


def test_fraud_event_items_do_not_return_raw_html() -> None:
    item = build_fraud_event_item(
        {
            "_id": "event-1",
            "visitor_id": "visitor-1",
            "event_type": "TEST",
            "severity": "HIGH",
            "action": '<img src=x onerror=alert(1)>',
            "allowed": False,
            "reason": '<script>alert(1)</script>',
            "risk_score": 80,
            "risk_level": "HIGH",
            "user_agent": '<svg onload=alert(1)>',
            "metadata": {"message": '<script>alert(1)</script>'},
            "created_at": None,
        }
    )

    assert item.action == ""
    assert item.reason == "alert(1)"
    assert item.user_agent == ""
    assert item.metadata["message"] == "alert(1)"


def test_generated_pdf_escapes_user_content(monkeypatch, tmp_path: Path) -> None:
    captured: list[str] = []

    class _DummyDoc:
        def __init__(self, _path: str, pagesize: object) -> None:
            self.path = _path
            self.pagesize = pagesize

        def build(self, _story: list[object]) -> None:
            return None

    def _capture_paragraph(text: str, style: object) -> tuple[str, object]:
        captured.append(text)
        return (text, style)

    monkeypatch.setattr("app.utils.pdf_generator.SimpleDocTemplate", _DummyDoc)
    monkeypatch.setattr("app.utils.pdf_generator.Paragraph", _capture_paragraph)

    generate_simple_pdf(
        title='<script>alert("xss")</script>',
        content='<img src=x onerror=alert("xss")>\nSecond line',
        output_dir=str(tmp_path),
    )

    assert captured[0] == '&lt;script&gt;alert("xss")&lt;/script&gt;'
    assert captured[-1] == '&lt;img src=x onerror=alert("xss")&gt;<br/>Second line'


def test_security_headers_include_csp_for_local_dev() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/public/config",
            "headers": [(b"origin", b"http://localhost:3025")],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "server": ("localhost", 8025),
        }
    )

    csp = _build_content_security_policy(request)

    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "http://localhost:3025" in csp


def test_sanitize_log_value_strips_tags_and_truncates() -> None:
    assert sanitize_log_value("<b>Hello</b>") == "Hello"
    assert len(sanitize_log_value("x" * 600)) == 512


def test_sanitize_mapping_redacts_sensitive_fields_recursively() -> None:
    sanitized = sanitize_mapping(
        {
            "email": "user@example.com",
            "password": "super-secret",
            "access_token": "access-secret",
            "refresh-token": "refresh-secret",
            "authorization": "Bearer secret",
            "cookie": "session=secret",
            "api_key": "api-secret",
            "clientSecret": "client-secret",
            "profile": {
                "display_name": "<b>Ada</b>",
                "tokens": ["secret-token"],
                "attempts": 2,
                "enabled": True,
                "empty": None,
            },
            "events": [{"message": "<script>alert(1)</script>", "token": "nested-secret"}],
        }
    )

    assert sanitized["email"] == "user@example.com"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["refresh-token"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["cookie"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["clientSecret"] == "[REDACTED]"
    assert sanitized["profile"]["display_name"] == "Ada"
    assert sanitized["profile"]["tokens"] == "[REDACTED]"
    assert sanitized["profile"]["attempts"] == 2
    assert sanitized["profile"]["enabled"] is True
    assert sanitized["profile"]["empty"] is None
    assert sanitized["events"][0]["message"] == "alert(1)"
    assert sanitized["events"][0]["token"] == "[REDACTED]"


def test_sanitize_mapping_handles_none() -> None:
    assert sanitize_mapping(None) == {}
