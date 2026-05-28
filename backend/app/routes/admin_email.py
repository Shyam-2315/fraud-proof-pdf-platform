from fastapi import APIRouter, Depends, Request

from app.core.admin_auth import require_admin_api_key
from app.schemas.admin import (
    AdminEmailStatusResponse,
    AdminEmailTestRequest,
    AdminEmailTestResponse,
)
from app.services.email_service import EmailService
from app.services.rate_limit_service import RateLimitService, client_ip

router = APIRouter(
    prefix="/admin/email",
    tags=["Admin Email"],
    dependencies=[Depends(require_admin_api_key)],
)
email_service = EmailService()
rate_limit_service = RateLimitService()


@router.get("/status", response_model=AdminEmailStatusResponse, response_model_exclude_none=True)
async def email_status(request: Request) -> AdminEmailStatusResponse:
    """
    Return the configured admin email delivery status.

    Args:
        request: Incoming HTTP request used for admin rate limiting.

    Returns:
        Sanitized email provider configuration and readiness information.
    """
    await _enforce_admin_rate_limit(request)
    return AdminEmailStatusResponse(**email_service.get_status())


@router.post("/test", response_model=AdminEmailTestResponse)
async def send_test_email(
    payload: AdminEmailTestRequest,
    request: Request,
) -> AdminEmailTestResponse:
    """
    Send a test email through the configured provider.

    Args:
        payload: Target email address for the test message.
        request: Incoming HTTP request used for admin rate limiting.

    Returns:
        Success confirmation after the provider accepts the test email.
    """
    await _enforce_admin_rate_limit(request)
    await email_service.send_test_email(to_email=payload.to)
    return AdminEmailTestResponse(success=True, message="Test email sent.")


async def _enforce_admin_rate_limit(request: Request) -> None:
    """
    Apply the shared admin email rate limit to the current request.

    Args:
        request: Incoming HTTP request whose client identity is rate limited.
    """
    await rate_limit_service.check(
        request,
        bucket="admin_email",
        identifier=client_ip(request),
        rate=email_service.settings.ADMIN_RATE_LIMIT,
    )
