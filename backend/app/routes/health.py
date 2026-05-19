from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import ping_mongo
from app.redis_client import ping_redis

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "port": settings.APP_PORT,
    }


@router.get("/health/db")
async def health_db() -> JSONResponse:
    try:
        await ping_mongo()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "mongodb",
                "detail": str(exc),
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "mongodb",
        },
    )


@router.get("/health/redis")
async def health_redis() -> JSONResponse:
    try:
        await ping_redis()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "redis",
                "detail": str(exc),
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "redis",
        },
    )
