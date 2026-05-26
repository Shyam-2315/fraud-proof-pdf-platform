import asyncio
import logging
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return all(
            [
                self.settings.EMAIL_PROVIDER == "SMTP",
                self.settings.SMTP_HOST,
                self.settings.SMTP_PORT,
                self.settings.SMTP_USERNAME,
                self.settings.SMTP_PASSWORD,
                self.settings.SMTP_FROM_EMAIL,
            ]
        )

    async def send_verification_code(self, *, email: str, code: str) -> None:
        if not self.is_configured():
            if self.settings.APP_ENV.lower() == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Email service is not configured.",
                )
            logger.info("Email verification code email=%s code=%s", email, code)
            return

        message = EmailMessage()
        message["Subject"] = f"{self.settings.SMTP_FROM_NAME} verification code"
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
        try:
            await asyncio.to_thread(self._send_smtp_message, message)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Email send failed email=%s", email)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send verification email right now.",
            ) from exc

    def _send_smtp_message(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10) as server:
            if self.settings.SMTP_USE_TLS:
                server.starttls()
            server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
            server.send_message(message)

    def _from_header(self) -> str:
        from_name = self.settings.SMTP_FROM_NAME.strip()
        from_email = self.settings.SMTP_FROM_EMAIL.strip()
        if from_name:
            return f"{from_name} <{from_email}>"
        return from_email
