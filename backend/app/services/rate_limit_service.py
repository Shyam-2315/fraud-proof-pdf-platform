import logging
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.middleware.rate_limiter import parse_rate_limit, sliding_window_bucket
from app.redis_client import get_redis
from app.utils.request_utils import get_client_ip

logger = logging.getLogger(__name__)


class RateLimitService:
    async def check(
        self,
        request: Request,
        bucket: str,
        identifier: str,
        rate: str,
    ) -> None:
        if not get_settings().RATE_LIMIT_ENABLED:
            return
        parsed = parse_rate_limit(rate)
        current_bucket = sliding_window_bucket(
            datetime.now(UTC).timestamp(),
            parsed.window_seconds,
        )
        key = f"rate:{bucket}:{identifier}:{current_bucket}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, parsed.window_seconds)
            if int(count) > parsed.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait a moment and try again.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Rate limit skipped bucket=%s error=%s", bucket, exc)


def client_ip(request: Request) -> str:
    return get_client_ip(request)
