import asyncio
import logging
import smtplib
from email.message import EmailMessage

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
    service = _build_email_service(monkeypatch, SMTP_PORT="587", SMTP_USE_TLS="true")
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
    assert "email_send_failed provider=SMTP host=smtp.gmail.com port=587" in caplog.text


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
    assert status_payload["smtp_mode"] == "STARTTLS"
    assert status_payload["smtp_password_configured"] is True
    assert "SMTP_PASSWORD" not in status_payload
    assert "smtp_password" not in status_payload
