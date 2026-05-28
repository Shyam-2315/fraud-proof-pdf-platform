from hmac import compare_digest

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings
from app.core.auth import get_authorization_token_optional, get_current_user_optional
from app.models.user import UserRole


async def require_admin_api_key(
    request: Request,
    x_admin_api_key: str | None = Header(
        default=None,
        alias="X-Admin-API-Key",
        description="Admin API key for fraud monitoring endpoints.",
    ),
) -> None:
    """
    Authorize an admin request using either an API key or admin bearer token.

    Args:
        request: Incoming HTTP request for an admin-only endpoint.
        x_admin_api_key: Optional admin API key header value.

    Returns:
        None. The request is authorized when no exception is raised.

    Raises:
        HTTPException: If the caller is not authorized for admin access.
    """
    if x_admin_api_key is not None:
        expected_key = get_settings().ADMIN_API_KEY
        if compare_digest(x_admin_api_key, expected_key):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )

    if get_authorization_token_optional(request) is not None:
        user = await get_current_user_optional(request)
        if user is not None and user.get("role") == UserRole.ADMIN.value:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin API key required",
    )
