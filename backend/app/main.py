"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.legacy.router import router as legacy_api_router
from app.api.v1.router import router as v1_api_router
from app.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.logging import configure_logging
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
from app.redis_client import close_redis_connection, connect_to_redis
from app.repositories.admin_audit_repository import ensure_admin_audit_indexes
from app.repositories.anonymous_ip_usage_repository import ensure_anonymous_ip_usage_indexes
from app.repositories.behavior_repository import ensure_behavior_indexes
from app.repositories.email_verification_repository import ensure_email_verification_indexes
from app.repositories.fraud_engine_repository import ensure_fraud_engine_indexes
from app.repositories.fraud_event_repository import ensure_fraud_event_indexes
from app.repositories.fraud_repository import ensure_fraud_indexes
from app.repositories.identity_repository import ensure_identity_link_indexes
from app.repositories.pdf_repository import ensure_pdf_indexes
from app.repositories.refresh_token_repository import ensure_refresh_token_indexes
from app.repositories.risk_repository import ensure_risk_indexes
from app.repositories.user_repository import ensure_user_indexes, seed_default_admin
from app.repositories.user_usage_repository import ensure_user_usage_indexes
from app.repositories.visitor_repository import ensure_visitor_indexes
from app.routes.health import router as health_router

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    Initialize and tear down application dependencies for the process lifetime.

    Args:
        _app: FastAPI application instance using this lifespan hook.

    Returns:
        Async iterator that yields once startup initialization has completed.
    """
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
        await ensure_anonymous_ip_usage_indexes()
        await ensure_pdf_indexes()
        await ensure_user_indexes()
        await ensure_refresh_token_indexes()
        await ensure_email_verification_indexes()
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


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Returns:
        Configured FastAPI application with middleware and routers attached.
    """
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
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(health_router)
    app.include_router(v1_api_router)
    app.include_router(legacy_api_router)
    return app


app = create_app()
