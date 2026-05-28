from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import ping_mongo
from app.redis_client import ping_redis

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health() -> dict[str, str | int]:
    """
    Return a lightweight service health summary.

    Returns:
        Basic application metadata and the listening port.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "port": settings.APP_PORT,
    }


@router.get("/live")
async def live() -> dict[str, str]:
    """
    Return a liveness response for container orchestrators.

    Returns:
        Static alive status when the process is running.
    """
    return {"status": "alive"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """
    Run dependency and storage readiness checks.

    Returns:
        JSON response describing readiness and individual subsystem checks.
    """
    checks: dict[str, bool | str] = {}

    try:
        await ping_mongo()
        checks["mongodb"] = True
    except Exception as exc:
        checks["mongodb"] = f"failed: {exc}"

    try:
        await ping_redis()
        checks["redis"] = True
    except Exception as exc:
        checks["redis"] = f"failed: {exc}"

    checks["storage_writable"] = _directory_writable(settings.PDF_STORAGE_DIR)
    checks["models_readable"] = _directory_readable(settings.ML_MODELS_DIR)
    is_ready = all(value is True for value in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
        },
    )


@router.get("/health/db")
async def health_db() -> JSONResponse:
    """
    Verify that MongoDB is reachable.

    Returns:
        Health response for the MongoDB dependency.
    """
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


def _directory_writable(path: str) -> bool | str:
    """
    Check whether the configured storage directory is writable.

    Args:
        path: Filesystem directory path to validate.

    Returns:
        True when the directory is writable, otherwise a failure message.
    """
    try:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=directory, prefix=".ready-", delete=True):
            pass
        return True
    except Exception as exc:
        return f"failed: {exc}"


def _directory_readable(path: str) -> bool | str:
    """
    Check whether the configured model directory is readable.

    Args:
        path: Filesystem directory path to validate.

    Returns:
        True when the directory is readable, otherwise a failure message.
    """
    try:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            return "failed: not a directory"
        next(directory.iterdir(), None)
        return True
    except StopIteration:
        return True
    except Exception as exc:
        return f"failed: {exc}"


@router.get("/health/redis")
async def health_redis() -> JSONResponse:
    """
    Verify that Redis is reachable.

    Returns:
        Health response for the Redis dependency.
    """
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
