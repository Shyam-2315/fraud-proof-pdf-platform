from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.public_config import (
    CUSTOMER_COOKIE_NAME,
    LOGIN_REQUIRED_MESSAGE,
    customer_cookie_options,
)
from app.schemas.visitor import (
    VisitorIdentifyRequest,
    VisitorIdentifyResponse,
    VisitorStatusResponse,
)
from app.services.anonymous_usage_service import AnonymousUsageService
from app.services.visitor_service import VisitorService
from app.services.rate_limit_service import RateLimitService, client_ip

router = APIRouter(prefix="/api/visitor", tags=["Visitor"])
visitor_service = VisitorService()
rate_limit_service = RateLimitService()
anonymous_usage_service = AnonymousUsageService()

ANON_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


@router.post("/identify", response_model=VisitorIdentifyResponse)
async def identify_visitor(
    payload: VisitorIdentifyRequest,
    request: Request,
    response: Response,
) -> VisitorIdentifyResponse:
    await rate_limit_service.check(
        request,
        bucket="visitor_identify",
        identifier=client_ip(request),
        limit=60,
        window_seconds=3600,
    )
    try:
        visitor, is_new_visitor, cookie_id = await visitor_service.identify_visitor(
            request=request,
            payload=payload,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to identify visitor.",
        ) from exc

    response.set_cookie(
        key=CUSTOMER_COOKIE_NAME,
        value=cookie_id,
        max_age=ANON_COOKIE_MAX_AGE,
        **customer_cookie_options(),
    )

    return VisitorIdentifyResponse(
        success=True,
        visitor_id=visitor["_id"],
        message="Ready to generate PDFs.",
    )


@router.get("/status", response_model=VisitorStatusResponse)
async def visitor_status(request: Request) -> VisitorStatusResponse:
    visitor = await visitor_service.find_visitor_from_request(request)
    if visitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visitor not found. Please identify visitor first.",
        )

    usage_summary = await anonymous_usage_service.build_shared_usage_summary(
        visitor=visitor,
        ip_address=client_ip(request),
    )
    requires_login = (
        bool(visitor.get("is_blocked", False))
        or usage_summary["remaining_free_uses"] <= 0
    )
    return VisitorStatusResponse(
        visitor_id=visitor["_id"],
        **usage_summary,
        is_blocked=bool(visitor.get("is_blocked", False)),
        message=(
            LOGIN_REQUIRED_MESSAGE
            if requires_login
            else _build_customer_status_message(usage_summary["remaining_free_uses"])
        ),
        requires_login=requires_login,
    )


def _build_customer_status_message(remaining_free_uses: int) -> str:
    if remaining_free_uses == 1:
        return "You have 1 free PDF generation remaining."
    return f"You have {remaining_free_uses} free PDF generations remaining."
