import logging

from fastapi import HTTPException, Request, status

from app.redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimitService:
    async def check(
        self,
        request: Request,
        bucket: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        key = f"rate:{bucket}:{identifier}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            if int(count) > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Rate limit skipped bucket=%s error=%s", bucket, exc)


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
