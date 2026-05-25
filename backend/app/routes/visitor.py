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
from app.utils.request_utils import get_normalized_client_ip

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
        rate=anonymous_usage_service.settings.VISITOR_IDENTIFY_RATE_LIMIT,
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
    await rate_limit_service.check(
        request,
        bucket="visitor_status",
        identifier=client_ip(request),
        rate=anonymous_usage_service.settings.VISITOR_STATUS_RATE_LIMIT,
    )
    visitor = await visitor_service.find_visitor_from_request(request)
    if visitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not start your session. Please refresh and try again.",
        )

    usage_summary = await anonymous_usage_service.build_shared_usage_summary(
        visitor=visitor,
        ip_address=get_normalized_client_ip(request),
    )
    shared_limit_reached = usage_summary["remaining_free_uses"] <= 0
    is_blocked = bool(visitor.get("is_blocked", False)) or shared_limit_reached
    requires_login = is_blocked
    return VisitorStatusResponse(
        visitor_id=visitor["_id"],
        **usage_summary,
        is_blocked=is_blocked,
        message=LOGIN_REQUIRED_MESSAGE if requires_login else None,
        requires_login=requires_login,
    )
