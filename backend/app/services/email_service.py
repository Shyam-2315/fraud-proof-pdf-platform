import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return not self.missing_config_fields()

    def missing_config_fields(self) -> list[str]:
        if self.settings.EMAIL_PROVIDER == "BREVO_API":
            missing: list[str] = []
            if not self.settings.BREVO_API_KEY:
                missing.append("BREVO_API_KEY")
            if not self.settings.BREVO_FROM_EMAIL:
                missing.append("BREVO_FROM_EMAIL")
            return missing

        if self.settings.EMAIL_PROVIDER == "SMTP":
            missing = []
            if not self.settings.SMTP_HOST:
                missing.append("SMTP_HOST")
            if not int(self.settings.SMTP_PORT):
                missing.append("SMTP_PORT")
            if not self.settings.SMTP_USERNAME:
                missing.append("SMTP_USERNAME")
            if not self.settings.SMTP_PASSWORD:
                missing.append("SMTP_PASSWORD")
            if not self.settings.SMTP_FROM_EMAIL:
                missing.append("SMTP_FROM_EMAIL")
            return missing

        return ["EMAIL_PROVIDER"]

    async def send_verification_code(self, *, email: str, code: str) -> None:
        if not self.is_configured():
            missing_fields = self.missing_config_fields()
            if self.settings.APP_ENV.lower() == "production":
                logger.error(
                    "email_service_config_missing provider=%s missing_fields=%s",
                    self.settings.EMAIL_PROVIDER,
                    ",".join(missing_fields),
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Email service is temporarily unavailable. Please try again later.",
                )
            logger.info("Email service is not configured; skipping verification email delivery email=%s", email)
            return

        message = self._build_verification_message(email=email, code=code)
        await self._deliver_message(message, secret_values=[code])

    async def send_test_email(self, *, to_email: str) -> None:
        if not self.is_configured():
            missing_fields = self.missing_config_fields()
            logger.error(
                "email_service_config_missing provider=%s missing_fields=%s",
                self.settings.EMAIL_PROVIDER,
                ",".join(missing_fields),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email service is temporarily unavailable. Please try again later.",
            )

        message = EmailMessage()
        message["Subject"] = f"{self.settings.APP_NAME} email delivery test"
        message["From"] = self._from_header()
        message["To"] = to_email
        message.set_content(
            "\n".join(
                [
                    f"This is a test email from {self.settings.APP_NAME}.",
                    "",
                    f"Delivery provider: {self.settings.EMAIL_PROVIDER}.",
                ]
            )
        )
        await self._deliver_message(message)

    def _send_smtp_message(self, message: EmailMessage) -> None:
        with self._create_smtp_client() as server:
            if self._should_starttls():
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
            server.send_message(message)

    async def _send_brevo_api_message(self, message: EmailMessage) -> None:
        payload = {
            "sender": {
                "name": self.settings.BREVO_FROM_NAME or self.settings.APP_NAME,
                "email": self.settings.BREVO_FROM_EMAIL,
            },
            "to": [{"email": value.strip()} for value in message.get_all("To", []) if value.strip()],
            "subject": message.get("Subject", ""),
            "textContent": message.get_content(),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                BREVO_API_URL,
                headers={
                    "accept": "application/json",
                    "api-key": self.settings.BREVO_API_KEY,
                    "content-type": "application/json",
                },
                json=payload,
            )
        if response.is_error:
            raise RuntimeError(f"Brevo API returned status={response.status_code}")

    def _create_smtp_client(self) -> Any:
        if self._uses_implicit_ssl():
            return smtplib.SMTP_SSL(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10)
        return smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10)

    async def _deliver_message(self, message: EmailMessage, secret_values: list[str] | None = None) -> None:
        try:
            if self.settings.EMAIL_PROVIDER == "BREVO_API":
                await self._send_brevo_api_message(message)
            elif self.settings.EMAIL_PROVIDER == "SMTP":
                await asyncio.to_thread(self._send_smtp_message, message)
            else:
                raise RuntimeError(f"Unsupported email provider: {self.settings.EMAIL_PROVIDER}")
        except Exception as exc:
            logger.error(
                "email_send_failed provider=%s error_type=%s error_message=%s",
                self.settings.EMAIL_PROVIDER,
                exc.__class__.__name__,
                self._safe_exception_message(exc, secret_values or []),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email service is temporarily unavailable. Please try again later.",
            ) from exc

    def get_status(self) -> dict[str, Any]:
        if self.settings.EMAIL_PROVIDER == "BREVO_API":
            return {
                "provider": self.settings.EMAIL_PROVIDER,
                "brevo_api_key_configured": bool(self.settings.BREVO_API_KEY),
                "brevo_from_email": self.settings.BREVO_FROM_EMAIL or None,
                "brevo_from_name": self.settings.BREVO_FROM_NAME or None,
                "delivery_mode": self._delivery_mode(),
                "ready": self.is_configured(),
            }

        if self.settings.EMAIL_PROVIDER == "SMTP":
            return {
                "provider": self.settings.EMAIL_PROVIDER,
                "smtp_host": self.settings.SMTP_HOST or None,
                "smtp_port": self.settings.SMTP_PORT if self.settings.SMTP_HOST else None,
                "smtp_username_configured": bool(self.settings.SMTP_USERNAME),
                "smtp_password_configured": bool(self.settings.SMTP_PASSWORD),
                "smtp_from_email": self.settings.SMTP_FROM_EMAIL or None,
                "smtp_use_tls": self.settings.SMTP_USE_TLS,
                "smtp_use_ssl": self.settings.SMTP_USE_SSL,
                "smtp_mode": self._smtp_mode(),
                "delivery_mode": self._delivery_mode(),
                "ready": self.is_configured(),
            }

        return {
            "provider": self.settings.EMAIL_PROVIDER,
            "delivery_mode": self._delivery_mode(),
            "ready": False,
        }

    def _build_verification_message(self, *, email: str, code: str) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = f"{self.settings.APP_NAME} verification code"
        message["From"] = self._from_header()
        message["To"] = email
        message.set_content(
            "\n".join(
                [
                    f"Your {self.settings.APP_NAME} verification code is: {code}",
                    "",
                    f"This code expires in {self.settings.EMAIL_VERIFICATION_OTP_TTL_MINUTES} minutes.",
                    "If you did not request this, you can ignore this email.",
                ]
            )
        )
        return message

    def _safe_exception_message(self, exc: Exception, secret_values: list[str]) -> str:
        message = str(exc) or exc.__class__.__name__
        for secret in [
            self.settings.SMTP_PASSWORD,
            self.settings.BREVO_API_KEY,
            *secret_values,
        ]:
            if secret:
                message = message.replace(secret, "[REDACTED]")
        return message

    def _smtp_mode(self) -> str:
        if self._uses_implicit_ssl():
            return "SSL"
        if self._should_starttls():
            return "STARTTLS"
        return "PLAIN"

    def _delivery_mode(self) -> str:
        if self.settings.EMAIL_PROVIDER == "BREVO_API":
            return "HTTPS_API"
        if self.settings.EMAIL_PROVIDER == "SMTP":
            return self._smtp_mode()
        return "UNKNOWN"

    def _from_header(self) -> str:
        if self.settings.EMAIL_PROVIDER == "BREVO_API":
            from_name = self.settings.BREVO_FROM_NAME.strip()
            from_email = self.settings.BREVO_FROM_EMAIL.strip()
        else:
            from_name = self.settings.SMTP_FROM_NAME.strip()
            from_email = self.settings.SMTP_FROM_EMAIL.strip()
        if from_name:
            return f"{from_name} <{from_email}>"
        return from_email

    def _uses_implicit_ssl(self) -> bool:
        return self.settings.SMTP_PORT == 465

    def _should_starttls(self) -> bool:
        if self._uses_implicit_ssl():
            return False
        if self.settings.SMTP_PORT == 587:
            return True
        return self.settings.SMTP_USE_TLS
