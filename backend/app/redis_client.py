import logging
from urllib.parse import urlsplit

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None
_redis_error: str | None = None


def _redis_target(redis_url: str) -> str:
    """Return a redacted Redis target for logging."""
    parts = urlsplit(redis_url)
    host = parts.hostname or "unknown"
    port = f":{parts.port}" if parts.port else ""
    scheme = parts.scheme or "redis"
    return f"{scheme}://{host}{port}"


async def connect_to_redis() -> None:
    """
    Open the Redis client if the configured endpoint is reachable.

    Returns:
        None. The shared Redis client is cached globally when available.
    """
    global _redis, _redis_error

    settings = get_settings()
    if _redis is not None:
        try:
            await _redis.ping()
            return
        except Exception as exc:
            logger.warning("Existing Redis client ping failed; reconnecting error=%s", exc)
            await _redis.aclose()
            _redis = None

    if not settings.REDIS_URL:
        _redis_error = "Redis URL is not configured."
        if settings.APP_ENV == "local":
            logger.info("Redis disabled in local environment because REDIS_URL is empty")
        else:
            logger.warning(
                "Redis URL is not configured environment=%s",
                settings.APP_ENV,
            )
        return

    client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
        retry_on_timeout=False,
        health_check_interval=30,
    )
    try:
        await client.ping()
        _redis = client
        _redis_error = None
        logger.info(
            "Connected to Redis target=%s",
            _redis_target(settings.REDIS_URL),
        )
    except Exception as exc:
        _redis_error = f"Redis connection failed: {exc}"
        logger.exception(
            "Redis initialization failed target=%s environment=%s",
            _redis_target(settings.REDIS_URL),
            settings.APP_ENV,
        )
        await client.aclose()
        _redis = None


async def close_redis_connection() -> None:
    """
    Close the shared Redis connection if it is open.

    Returns:
        None. Cached Redis state is cleared.
    """
    global _redis, _redis_error

    if _redis is not None:
        await _redis.aclose()
        logger.info("Closed Redis connection")

    _redis = None
    _redis_error = None


def get_redis() -> Redis:
    """
    Return the active Redis client.

    Returns:
        Connected Redis client instance.

    Raises:
        RuntimeError: If Redis has not been connected yet.
    """
    if _redis is None:
        raise RuntimeError(_redis_error or "Redis is not connected")
    return _redis


async def ping_redis() -> bool:
    """
    Run a ping command against the shared Redis client.

    Returns:
        True when Redis responds successfully.

    Raises:
        RuntimeError: If the Redis client has not been initialized.
    """
    if _redis is None:
        raise RuntimeError(_redis_error or "Redis client is not initialized")

    return bool(await _redis.ping())
