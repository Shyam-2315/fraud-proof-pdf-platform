"""Admin endpoints for API v1."""

from fastapi import APIRouter

from app.routes.admin_email import router as admin_email_router
from app.routes.admin_fraud import router as admin_fraud_router

router = APIRouter()
router.include_router(admin_fraud_router)
router.include_router(admin_email_router)
