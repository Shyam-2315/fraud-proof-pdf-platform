import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx
import pytest
from fastapi import HTTPException

from app.services.email_service import EmailService
from conftest import apply_test_env


class _FakeSMTPServer:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.sent_messages: list[EmailMessage] = []

    def __enter__(self) -> "_FakeSMTPServer":
        self.calls.append("enter")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.calls.append("exit")

    def starttls(self) -> None:
        self.calls.append("starttls")

    def ehlo(self) -> None:
        self.calls.append("ehlo")

    def login(self, username: str, password: str) -> None:
        self.calls.append(f"login:{username}:{password}")

    def send_message(self, message: EmailMessage) -> None:
        self.calls.append("send_message")
        self.sent_messages.append(message)


class _FakeBrevoResponse:
    def __init__(self, status_code: int = 201) -> None:
        self.status_code = status_code

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400


class _FakeBrevoClient:
    def __init__(self, *, status_code: int = 201) -> None:
        self.status_code = status_code
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> "_FakeBrevoClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> _FakeBrevoResponse:
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _FakeBrevoResponse(status_code=self.status_code)


def _build_email_service(monkeypatch, **env: str) -> EmailService:
    apply_test_env(
        monkeypatch,
        APP_ENV="development",
        EMAIL_PROVIDER="SMTP",
        SMTP_HOST="smtp.gmail.com",
        SMTP_PORT="587",
        SMTP_USERNAME="mailer@example.com",
        SMTP_PASSWORD="super-secret-password",
        SMTP_FROM_EMAIL="noreply@example.com",
        SMTP_FROM_NAME="PDFCraft",
        SMTP_USE_TLS="true",
        SMTP_USE_SSL="false",
        **env,
    )
    return EmailService()


def _build_message() -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Verification"
    message["From"] = "PDFCraft <noreply@example.com>"
    message["To"] = "user@example.com"
    message.set_content("Verification email")
    return message


def test_send_smtp_message_uses_starttls_for_port_587(monkeypatch) -> None:
    service = _build_email_service(monkeypatch, SMTP_PORT="587", SMTP_USE_TLS="false")
    smtp_server = _FakeSMTPServer()
    smtp_calls: list[tuple[str, str, int, int]] = []
    smtp_ssl_calls: list[tuple[str, str, int, int]] = []

    def fake_smtp(host: str, port: int, timeout: int) -> _FakeSMTPServer:
        smtp_calls.append(("smtp", host, port, timeout))
        return smtp_server

    def fake_smtp_ssl(host: str, port: int, timeout: int) -> _FakeSMTPServer:
        smtp_ssl_calls.append(("smtp_ssl", host, port, timeout))
        return smtp_server

    monkeypatch.setattr(smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(smtplib, "SMTP_SSL", fake_smtp_ssl)

    service._send_smtp_message(_build_message())

    assert smtp_calls == [("smtp", "smtp.gmail.com", 587, 10)]
    assert smtp_ssl_calls == []
    assert smtp_server.calls == [
        "enter",
        "ehlo",
        "starttls",
        "ehlo",
        "login:mailer@example.com:super-secret-password",
        "send_message",
        "exit",
    ]


def test_send_smtp_message_uses_ssl_for_port_465(monkeypatch) -> None:
    service = _build_email_service(monkeypatch, SMTP_PORT="465", SMTP_USE_TLS="true")
    smtp_server = _FakeSMTPServer()
    smtp_calls: list[tuple[str, str, int, int]] = []
    smtp_ssl_calls: list[tuple[str, str, int, int]] = []

    def fake_smtp(host: str, port: int, timeout: int) -> _FakeSMTPServer:
        smtp_calls.append(("smtp", host, port, timeout))
        return smtp_server

    def fake_smtp_ssl(host: str, port: int, timeout: int) -> _FakeSMTPServer:
        smtp_ssl_calls.append(("smtp_ssl", host, port, timeout))
        return smtp_server

    monkeypatch.setattr(smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(smtplib, "SMTP_SSL", fake_smtp_ssl)

    service._send_smtp_message(_build_message())

    assert smtp_calls == []
    assert smtp_ssl_calls == [("smtp_ssl", "smtp.gmail.com", 465, 10)]
    assert smtp_server.calls == [
        "enter",
        "login:mailer@example.com:super-secret-password",
        "send_message",
        "exit",
    ]


def test_send_verification_code_logs_safe_failure_details(monkeypatch, caplog) -> None:
    service = _build_email_service(monkeypatch)
    otp_code = "123456"

    def fake_send(_: EmailMessage) -> None:
        raise RuntimeError(f"login failed password=super-secret-password otp={otp_code}")

    monkeypatch.setattr(service, "_send_smtp_message", fake_send)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(service.send_verification_code(email="user@example.com", code=otp_code))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Email service is temporarily unavailable. Please try again later."
    assert "RuntimeError" in caplog.text
    assert "[REDACTED]" in caplog.text
    assert "super-secret-password" not in caplog.text
    assert otp_code not in caplog.text
    assert "email_send_failed provider=SMTP error_type=RuntimeError" in caplog.text


def test_send_verification_code_without_smtp_does_not_log_otp(monkeypatch, caplog) -> None:
    service = _build_email_service(
        monkeypatch,
        SMTP_HOST="",
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
    )
    otp_code = "654321"

    with caplog.at_level(logging.INFO):
        asyncio.run(service.send_verification_code(email="user@example.com", code=otp_code))

    assert "user@example.com" in caplog.text
    assert otp_code not in caplog.text
    assert "Email service is not configured; skipping verification email delivery" in caplog.text


def test_send_verification_code_missing_smtp_in_production_returns_safe_503(monkeypatch, caplog) -> None:
    service = _build_email_service(
        monkeypatch,
        APP_ENV="production",
        SMTP_HOST="",
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(service.send_verification_code(email="user@example.com", code="123456"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Email service is temporarily unavailable. Please try again later."
    assert "email_service_config_missing provider=SMTP missing_fields=SMTP_HOST,SMTP_USERNAME,SMTP_PASSWORD,SMTP_FROM_EMAIL" in caplog.text
    assert "123456" not in caplog.text


def test_smtp_password_spaces_are_stripped(monkeypatch) -> None:
    service = _build_email_service(monkeypatch, SMTP_PASSWORD="abcd efgh ijkl mnop")

    assert service.settings.SMTP_PASSWORD == "abcdefghijklmnop"


def test_admin_email_status_never_exposes_smtp_password(monkeypatch) -> None:
    service = _build_email_service(monkeypatch, SMTP_PORT="587", SMTP_USE_TLS="true")

    status_payload = service.get_status()

    assert status_payload["provider"] == "SMTP"
    assert status_payload["smtp_use_ssl"] is False
    assert status_payload["smtp_mode"] == "STARTTLS"
    assert status_payload["delivery_mode"] == "STARTTLS"
    assert status_payload["smtp_password_configured"] is True
    assert "SMTP_PASSWORD" not in status_payload
    assert "smtp_password" not in status_payload
    assert "BREVO_API_KEY" not in status_payload
    assert "brevo_api_key" not in status_payload
    assert "brevo_api_key_configured" not in status_payload


def test_send_verification_code_uses_brevo_api(monkeypatch) -> None:
    service = _build_email_service(
        monkeypatch,
        EMAIL_PROVIDER="BREVO_API",
        BREVO_API_KEY="brevo-secret-key",
        BREVO_FROM_EMAIL="sender@example.com",
        BREVO_FROM_NAME="PDFCraft",
        SMTP_HOST="",
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
    )
    fake_client = _FakeBrevoClient(status_code=201)

    def fake_async_client(*args, **kwargs) -> _FakeBrevoClient:
        assert kwargs["timeout"] == 10.0
        return fake_client

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    asyncio.run(service.send_verification_code(email="user@example.com", code="123456"))

    assert len(fake_client.calls) == 1
    request_payload = fake_client.calls[0]
    assert request_payload["url"] == "https://api.brevo.com/v3/smtp/email"
    assert request_payload["headers"]["api-key"] == "brevo-secret-key"
    assert request_payload["json"]["sender"] == {
        "name": "PDFCraft",
        "email": "sender@example.com",
    }
    assert request_payload["json"]["to"] == [{"email": "user@example.com"}]
    assert request_payload["json"]["subject"] == "PDFCraft verification code"
    assert "123456" in request_payload["json"]["textContent"]


def test_send_verification_code_brevo_failure_returns_safe_503(monkeypatch, caplog) -> None:
    service = _build_email_service(
        monkeypatch,
        EMAIL_PROVIDER="BREVO_API",
        BREVO_API_KEY="brevo-secret-key",
        BREVO_FROM_EMAIL="sender@example.com",
        BREVO_FROM_NAME="PDFCraft",
        SMTP_HOST="",
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
    )

    async def fake_send(_: EmailMessage) -> None:
        raise RuntimeError("Brevo delivery failed api_key=brevo-secret-key otp=123456")

    monkeypatch.setattr(service, "_send_brevo_api_message", fake_send)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(service.send_verification_code(email="user@example.com", code="123456"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Email service is temporarily unavailable. Please try again later."
    assert "provider=BREVO_API" in caplog.text
    assert "brevo-secret-key" not in caplog.text
    assert "123456" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_admin_email_status_never_exposes_brevo_api_key(monkeypatch) -> None:
    service = _build_email_service(
        monkeypatch,
        EMAIL_PROVIDER="BREVO_API",
        BREVO_API_KEY="brevo-secret-key",
        BREVO_FROM_EMAIL="sender@example.com",
        BREVO_FROM_NAME="PDFCraft",
        SMTP_HOST="",
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
    )

    status_payload = service.get_status()

    assert status_payload["provider"] == "BREVO_API"
    assert status_payload["ready"] is True
    assert status_payload["brevo_api_key_configured"] is True
    assert status_payload["brevo_from_email"] == "sender@example.com"
    assert status_payload["brevo_from_name"] == "PDFCraft"
    assert status_payload["delivery_mode"] == "HTTPS_API"
    assert "smtp_username_configured" not in status_payload
    assert "smtp_password_configured" not in status_payload
    assert "smtp_from_email" not in status_payload
    assert "BREVO_API_KEY" not in status_payload
    assert "brevo_api_key" not in status_payload


def test_admin_email_status_brevo_ready_depends_only_on_brevo_fields(monkeypatch) -> None:
    service = _build_email_service(
        monkeypatch,
        EMAIL_PROVIDER="BREVO_API",
        BREVO_API_KEY="brevo-secret-key",
        BREVO_FROM_EMAIL="sender@example.com",
        BREVO_FROM_NAME="PDFCraft",
        SMTP_HOST="",
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SMTP_FROM_EMAIL="",
    )

    status_payload = service.get_status()

    assert status_payload == {
        "provider": "BREVO_API",
        "brevo_api_key_configured": True,
        "brevo_from_email": "sender@example.com",
        "brevo_from_name": "PDFCraft",
        "delivery_mode": "HTTPS_API",
        "ready": True,
    }


def test_send_test_email_uses_same_brevo_readiness_check(monkeypatch) -> None:
    service = _build_email_service(
        monkeypatch,
        EMAIL_PROVIDER="BREVO_API",
        BREVO_API_KEY="",
        BREVO_FROM_EMAIL="",
        SMTP_HOST="smtp.gmail.com",
        SMTP_USERNAME="mailer@example.com",
        SMTP_PASSWORD="super-secret-password",
        SMTP_FROM_EMAIL="noreply@example.com",
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.send_test_email(to_email="user@example.com"))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Email service is temporarily unavailable. Please try again later."
