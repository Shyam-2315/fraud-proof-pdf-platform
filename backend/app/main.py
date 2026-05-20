import logging
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, UTC

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
from app.database import close_mongo_connection, connect_to_mongo
from app.repositories.admin_audit_repository import ensure_admin_audit_indexes
from app.repositories.fraud_event_repository import ensure_fraud_event_indexes
from app.repositories.fraud_engine_repository import ensure_fraud_engine_indexes
from app.repositories.fraud_repository import ensure_fraud_indexes
from app.repositories.behavior_repository import ensure_behavior_indexes
from app.repositories.identity_repository import ensure_identity_link_indexes
from app.repositories.pdf_repository import ensure_pdf_indexes
from app.repositories.refresh_token_repository import ensure_refresh_token_indexes
from app.repositories.risk_repository import ensure_risk_indexes
from app.repositories.user_repository import ensure_user_indexes, seed_default_admin
from app.repositories.user_usage_repository import ensure_user_usage_indexes
from app.repositories.visitor_repository import ensure_visitor_indexes
from app.redis_client import close_redis_connection, connect_to_redis
from app.routes import account, admin_fraud, auth, behavior, pdf, public, visitor
from app.routes.health import router as health_router

settings = get_settings()


class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler()
    if settings.JSON_LOGS:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting %s environment=%s secure_cookies=%s trust_proxy_headers=%s api_docs=%s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.SECURE_COOKIES,
        settings.TRUST_PROXY_HEADERS,
        settings.ENABLE_API_DOCS,
    )
    try:
        await connect_to_mongo()
        await ensure_visitor_indexes()
        await ensure_pdf_indexes()
        await ensure_user_indexes()
        await ensure_refresh_token_indexes()
        await ensure_user_usage_indexes()
        await ensure_fraud_indexes()
        await ensure_fraud_event_indexes()
        await ensure_identity_link_indexes()
        await ensure_risk_indexes()
        await ensure_behavior_indexes()
        await ensure_fraud_engine_indexes()
        await ensure_admin_audit_indexes()
        await seed_default_admin()
        await connect_to_redis()
        yield
    finally:
        await close_redis_connection()
        await close_mongo_connection()
        logger.info("Stopped %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_API_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health_router)
app.include_router(public.router)
app.include_router(visitor.router)
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(behavior.router)
app.include_router(pdf.router)
app.include_router(admin_fraud.router)
