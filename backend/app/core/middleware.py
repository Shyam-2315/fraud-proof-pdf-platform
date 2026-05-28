import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.request_utils import get_client_ip

logger = logging.getLogger("app.request")


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
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
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
        return response
