from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.auth import get_current_user
from app.schemas.auth import (
    AuthResponse,
    LogoutRequest,
    MeResponse,
    RefreshTokenRequest,
    TokenRefreshResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService
from app.services.rate_limit_service import RateLimitService, client_ip

router = APIRouter(prefix="/api/auth", tags=["Auth"])
auth_service = AuthService()
rate_limit_service = RateLimitService()
settings = get_settings()


@router.post("/register", response_model=AuthResponse)
async def register(
    payload: UserRegisterRequest,
    request: Request,
) -> AuthResponse:
    await rate_limit_service.check(
        request,
        bucket="auth_register",
        identifier=client_ip(request),
        rate=settings.AUTH_REGISTER_RATE_LIMIT,
    )
    return await auth_service.register_user(payload=payload, request=request)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: UserLoginRequest,
    request: Request,
) -> AuthResponse:
    await rate_limit_service.check(
        request,
        bucket="auth_login",
        identifier=f"{client_ip(request)}:{str(payload.email).lower()}",
        rate=settings.AUTH_LOGIN_RATE_LIMIT,
    )
    return await auth_service.login_user(payload=payload, request=request)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(payload: RefreshTokenRequest) -> TokenRefreshResponse:
    return await auth_service.refresh(payload=payload)


@router.post("/logout")
async def logout(payload: LogoutRequest) -> dict[str, bool | str]:
    return await auth_service.logout(payload=payload)


@router.get("/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    return auth_service.get_me(current_user=current_user)
