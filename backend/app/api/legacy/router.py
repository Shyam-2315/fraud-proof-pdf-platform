"""Legacy API router kept for backward compatibility."""

from fastapi import APIRouter

from app.api.v1.endpoints import account, admin, auth, behavior, pdf, public, visitor

router = APIRouter(prefix="/api")
router.include_router(public.router)
router.include_router(visitor.router)
router.include_router(auth.router)
router.include_router(account.router)
router.include_router(behavior.router)
router.include_router(pdf.router)
router.include_router(admin.router)
