import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.repositories.request_log_repository import RequestLogRepository
from app.utils.request_utils import get_client_ip
from app.utils.sanitization import sanitize_log_value

logger = logging.getLogger("app.request")
request_log_repository = RequestLogRepository()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Core infrastructure helper used by the application runtime.
    """
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Attach a stable request ID to the request state and response headers.

        Args:
            request: Incoming HTTP request being processed.
            call_next: Middleware callback that forwards the request.

        Returns:
            HTTP response with the request ID header attached.
        """
        request_id = sanitize_log_value(request.headers.get("X-Request-ID", str(uuid.uuid4())))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Core infrastructure helper used by the application runtime.
    """
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Record structured timing and request metadata for every request.

        Args:
            request: Incoming HTTP request being processed.
            call_next: Middleware callback that forwards the request.

        Returns:
            HTTP response produced by downstream handlers.
        """
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            client_ip = get_client_ip(request)
            request_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", ""))
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                },
            )
            logger.debug(
                "method=%s path=%s status_code=%s duration_ms=%s client_ip=%s request_id=%s",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                client_ip,
                request_id,
            )
            await _store_api_request_log(
                request=request,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                request_id=request_id,
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Core infrastructure helper used by the application runtime.
    """
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Apply a baseline set of security headers to every response.

        Args:
            request: Incoming HTTP request being processed.
            call_next: Middleware callback that forwards the request.

        Returns:
            HTTP response with security headers attached.
        """
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Content-Security-Policy"] = _build_content_security_policy(request)
        return response


async def _store_api_request_log(
    request: Request,
    status_code: int,
    duration_ms: float,
    client_ip: str,
    request_id: str,
) -> None:
    """
    Persist sanitized API request metadata for admin observability.

    Args:
        request: Incoming request whose metadata should be recorded.
        status_code: Final response status code.
        duration_ms: Request duration in milliseconds.
        client_ip: Normalized client IP value used by runtime logs.
        request_id: Request correlation identifier.
    """
    path = sanitize_log_value(request.url.path)
    if not path.startswith("/api"):
        return
    try:
        await request_log_repository.create_log(
            {
                "request_id": sanitize_log_value(request_id),
                "method": sanitize_log_value(request.method),
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": sanitize_log_value(client_ip),
                "block_reason": sanitize_log_value(getattr(request.state, "block_reason", None)),
                "fraud_score": getattr(request.state, "fraud_score", None),
            }
        )
    except Exception as exc:
        logger.warning(
            "Failed to persist request log request_id=%s path=%s error=%s",
            request_id,
            path,
            exc,
        )


def _build_content_security_policy(request: Request) -> str:
    """Return a strict CSP that preserves local development websocket traffic."""
    connect_src = ["'self'"]
    origin = request.headers.get("origin")
    if origin:
        connect_src.append(origin)
    if request.url.hostname in {"localhost", "127.0.0.1"}:
        connect_src.extend(["ws://localhost:*", "ws://127.0.0.1:*"])
    return (
        "default-src 'self'; "
        "script-src 'self'; "
        f"connect-src {' '.join(dict.fromkeys(connect_src))}; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
