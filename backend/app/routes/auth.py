from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.auth import get_current_user
from app.schemas.auth import (
    AuthResponse,
    LogoutRequest,
    MeResponse,
    RegisterResponse,
    RefreshTokenRequest,
    ResendVerificationRequest,
    TokenRefreshResponse,
    UserLoginRequest,
    UserRegisterRequest,
    VerificationResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.rate_limit_service import RateLimitService, client_ip

router = APIRouter(prefix="/api/auth", tags=["Auth"])
auth_service = AuthService()
rate_limit_service = RateLimitService()
settings = get_settings()


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: UserRegisterRequest,
    request: Request,
) -> RegisterResponse:
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


@router.post("/verify-email", response_model=VerificationResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
) -> VerificationResponse:
    await rate_limit_service.check(
        request,
        bucket="auth_verify_email",
        identifier=f"{client_ip(request)}:{payload.email}",
        rate=settings.AUTH_VERIFY_EMAIL_RATE_LIMIT,
    )
    return await auth_service.verify_email(payload=payload)


@router.post("/resend-verification", response_model=VerificationResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
) -> VerificationResponse:
    await rate_limit_service.check(
        request,
        bucket="auth_resend_verification",
        identifier=f"{client_ip(request)}:{payload.email}",
        rate=settings.AUTH_RESEND_VERIFICATION_RATE_LIMIT,
    )
    return await auth_service.resend_verification(payload=payload)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(payload: RefreshTokenRequest) -> TokenRefreshResponse:
    return await auth_service.refresh(payload=payload)


@router.post("/logout")
async def logout(payload: LogoutRequest) -> dict[str, bool | str]:
    return await auth_service.logout(payload=payload)


@router.get("/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    return auth_service.get_me(current_user=current_user)
