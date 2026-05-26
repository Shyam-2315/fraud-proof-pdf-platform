import logging

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def connect_to_redis() -> None:
    global _redis

    settings = get_settings()
    client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
        retry_on_timeout=False,
    )
    try:
        _redis = client
        await ping_redis()
        logger.info("Connected to Redis")
    except Exception as exc:
        logger.warning("Redis unavailable; continuing without Redis error=%s", exc)
        await client.aclose()
        _redis = None


async def close_redis_connection() -> None:
    global _redis

    if _redis is not None:
        await _redis.aclose()
        logger.info("Closed Redis connection")

    _redis = None


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis is not connected")
    return _redis


async def ping_redis() -> bool:
    if _redis is None:
        raise RuntimeError("Redis client is not initialized")

    return bool(await _redis.ping())
