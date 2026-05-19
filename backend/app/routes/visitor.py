from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.repositories.visitor_repository import VisitorRepository
from app.schemas.visitor import (
    TrackedSignals,
    VisitorIdentifyRequest,
    VisitorIdentifyResponse,
    VisitorStatusResponse,
)
from app.services.visitor_service import VisitorService, build_usage_summary

router = APIRouter(prefix="/api/visitor", tags=["Visitor"])
visitor_service = VisitorService()
visitor_repository = VisitorRepository()

ANON_COOKIE_NAME = "anon_id"
ANON_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


@router.post("/identify", response_model=VisitorIdentifyResponse)
async def identify_visitor(
    payload: VisitorIdentifyRequest,
    request: Request,
    response: Response,
) -> VisitorIdentifyResponse:
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
        key=ANON_COOKIE_NAME,
        value=cookie_id,
        max_age=ANON_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )

    usage_summary = build_usage_summary(visitor)
    return VisitorIdentifyResponse(
        visitor_id=visitor["_id"],
        is_new_visitor=is_new_visitor,
        **usage_summary,
        risk_score=int(visitor.get("risk_score", 0)),
        risk_level=str(visitor.get("risk_level", "LOW")),
        is_blocked=bool(visitor.get("is_blocked", False)),
        message=(
            "New anonymous visitor identified."
            if is_new_visitor
            else "Existing anonymous visitor recognized."
        ),
    )


@router.get("/status", response_model=VisitorStatusResponse)
async def visitor_status(request: Request) -> VisitorStatusResponse:
    cookie_id = request.cookies.get(ANON_COOKIE_NAME)
    if not cookie_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visitor cookie not found. Please identify visitor first.",
        )

    visitor = await visitor_repository.find_by_cookie_id(cookie_id)
    if visitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visitor not found.",
        )

    usage_summary = build_usage_summary(visitor)
    return VisitorStatusResponse(
        visitor_id=visitor["_id"],
        **usage_summary,
        risk_score=int(visitor.get("risk_score", 0)),
        risk_level=str(visitor.get("risk_level", "LOW")),
        is_blocked=bool(visitor.get("is_blocked", False)),
        block_reason=visitor.get("block_reason"),
        tracked_signals=_build_tracked_signals(visitor),
    )


def _build_tracked_signals(visitor: dict[str, Any]) -> TrackedSignals:
    return TrackedSignals(
        local_storage_ids=len(visitor.get("local_storage_ids", [])),
        session_ids=len(visitor.get("session_ids", [])),
        fingerprint_hashes=len(visitor.get("fingerprint_hashes", [])),
        ip_addresses=len(visitor.get("ip_addresses", [])),
        user_agents=len(visitor.get("user_agents", [])),
    )
