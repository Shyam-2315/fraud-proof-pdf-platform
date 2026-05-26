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
    prefix="/api/admin/email",
    tags=["Admin Email"],
    dependencies=[Depends(require_admin_api_key)],
)
email_service = EmailService()
rate_limit_service = RateLimitService()


@router.get("/status", response_model=AdminEmailStatusResponse, response_model_exclude_none=True)
async def email_status(request: Request) -> AdminEmailStatusResponse:
    await _enforce_admin_rate_limit(request)
    return AdminEmailStatusResponse(**email_service.get_status())


@router.post("/test", response_model=AdminEmailTestResponse)
async def send_test_email(
    payload: AdminEmailTestRequest,
    request: Request,
) -> AdminEmailTestResponse:
    await _enforce_admin_rate_limit(request)
    await email_service.send_test_email(to_email=payload.to)
    return AdminEmailTestResponse(success=True, message="Test email sent.")


async def _enforce_admin_rate_limit(request: Request) -> None:
    await rate_limit_service.check(
        request,
        bucket="admin_email",
        identifier=client_ip(request),
        rate=email_service.settings.ADMIN_RATE_LIMIT,
    )
