import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.public_config import CUSTOMER_COOKIE_NAME, customer_cookie_options
from app.schemas.visitor import (
    VisitorIdentifyRequest,
    VisitorIdentifyResponse,
    VisitorStatusResponse,
)
from app.services.anonymous_usage_service import AnonymousUsageService
from app.services.rate_limit_service import RateLimitService, client_ip
from app.services.visitor_service import VisitorService

router = APIRouter(prefix="/visitor", tags=["Visitor"])
visitor_service = VisitorService()
rate_limit_service = RateLimitService()
anonymous_usage_service = AnonymousUsageService()
logger = logging.getLogger(__name__)

ANON_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
SLOW_ENDPOINT_MS = 250


@router.post("/identify", response_model=VisitorIdentifyResponse)
async def identify_visitor(
    payload: VisitorIdentifyRequest,
    request: Request,
    response: Response,
) -> VisitorIdentifyResponse:
    """
    Resolve or create the anonymous visitor identity for the current browser.

    Args:
        payload: Browser and device continuity signals from the frontend.
        request: Incoming HTTP request used for risk checks and rate limiting.
        response: Outgoing response used to set the anonymous visitor cookie.

    Returns:
        Visitor identifier and readiness status for PDF generation.
    """
    started_at = perf_counter()
    try:
        await rate_limit_service.check(
            request=request,
            bucket="visitor_identify",
            identifier=client_ip(request),
            rate=anonymous_usage_service.settings.VISITOR_IDENTIFY_RATE_LIMIT,
        )
        visitor, _, cookie_id = await visitor_service.identify_visitor(request=request, payload=payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not start your session. Please refresh and try again.",
        ) from exc
    else:
        response.set_cookie(
            key=CUSTOMER_COOKIE_NAME,
            value=cookie_id,
            max_age=ANON_COOKIE_MAX_AGE,
            **customer_cookie_options(),
        )
        return VisitorIdentifyResponse(success=True, visitor_id=visitor["_id"], message="Ready to generate PDFs.")
    finally:
        duration_ms = (perf_counter() - started_at) * 1000
        if duration_ms >= SLOW_ENDPOINT_MS:
            logger.info("Slow endpoint path=%s duration_ms=%.2f", request.url.path, duration_ms)


@router.get("/status", response_model=VisitorStatusResponse, response_model_exclude_unset=True)
async def visitor_status(request: Request) -> VisitorStatusResponse:
    """
    Return the anonymous visitor's remaining free usage status.

    Args:
        request: Incoming HTTP request used to resolve visitor identity.

    Returns:
        Remaining quota, blocking state, and login requirement details.
    """
    started_at = perf_counter()
    try:
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

        usage_status = await anonymous_usage_service.get_anonymous_usage_status(
            request=request,
            visitor=visitor,
        )
        response_data = {
            "visitor_id": visitor["_id"],
            "used": int(usage_status["used"]),
            "remaining": int(usage_status["remaining"]),
            "free_limit": int(usage_status["free_limit"]),
            "free_usage_count": int(usage_status["free_usage_count"]),
            "free_usage_limit": int(usage_status["free_usage_limit"]),
            "remaining_free_uses": int(usage_status["remaining_free_uses"]),
            "is_blocked": bool(usage_status["is_blocked"]),
            "message": usage_status["message"],
            "requires_login": bool(usage_status["requires_login"]),
        }
        if usage_status["fraud_blocked"]:
            response_data["fraud_blocked"] = True
        return VisitorStatusResponse(
            **response_data,
        )
    finally:
        duration_ms = (perf_counter() - started_at) * 1000
        if duration_ms >= SLOW_ENDPOINT_MS:
            logger.info("Slow endpoint path=%s duration_ms=%.2f", request.url.path, duration_ms)
