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

router = APIRouter(prefix="/auth", tags=["Auth"])
auth_service = AuthService()
rate_limit_service = RateLimitService()
settings = get_settings()


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: UserRegisterRequest,
    request: Request,
) -> RegisterResponse:
    """
    Register a new customer account and start email verification.

    Args:
        payload: Validated customer registration fields.
        request: Incoming HTTP request used for rate limiting and context.

    Returns:
        Registration result including verification guidance.
    """
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
    """
    Authenticate a customer and return access credentials.

    Args:
        payload: Login credentials submitted by the customer.
        request: Incoming HTTP request used for rate limiting context.

    Returns:
        Access and refresh tokens plus authenticated user details.
    """
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
    """
    Verify a user's email address with the submitted OTP code.

    Args:
        payload: Email verification payload containing the email and OTP.
        request: Incoming HTTP request used for rate limiting.

    Returns:
        Verification status for the requested account.
    """
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
    """
    Resend an email verification code to an unverified user.

    Args:
        payload: Email address that should receive a new OTP.
        request: Incoming HTTP request used for rate limiting.

    Returns:
        Confirmation that the verification message was handled.
    """
    await rate_limit_service.check(
        request,
        bucket="auth_resend_verification",
        identifier=f"{client_ip(request)}:{payload.email}",
        rate=settings.AUTH_RESEND_VERIFICATION_RATE_LIMIT,
    )
    return await auth_service.resend_verification(payload=payload)


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(payload: RefreshTokenRequest) -> TokenRefreshResponse:
    """
    Exchange a refresh token for a new access token pair.

    Args:
        payload: Refresh token request payload.

    Returns:
        Newly issued authentication tokens.
    """
    return await auth_service.refresh(payload=payload)


@router.post("/logout")
async def logout(payload: LogoutRequest) -> dict[str, bool | str]:
    """
    Revoke a refresh token and log the current session out.

    Args:
        payload: Logout request containing the refresh token to revoke.

    Returns:
        Success status and user-facing logout message.
    """
    return await auth_service.logout(payload=payload)


@router.get("/me", response_model=MeResponse)
async def me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    """
    Return the currently authenticated user's profile.

    Args:
        current_user: Authenticated user loaded from the bearer token.

    Returns:
        Serialized profile details for the current user.
    """
    return auth_service.get_me(current_user=current_user)
