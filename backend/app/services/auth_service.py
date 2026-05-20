from typing import Any

from fastapi import HTTPException, Request, status
from pymongo.errors import DuplicateKeyError

from app.core.auth import hash_password, verify_password
from app.core.public_config import get_visitor_cookie
from app.models.fraud import FraudEventType, FraudSeverity
from app.models.user import UserPlan, UserRole
from app.repositories.pdf_repository import PDFRepository
from app.repositories.user_repository import UserRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.auth import (
    AuthResponse,
    LogoutRequest,
    MeResponse,
    RefreshTokenRequest,
    TokenRefreshResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.fraud_service import FraudService
from app.services.token_service import TokenService
from app.utils.security import generate_uuid, normalize_ip, utc_now


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_service: FraudService | None = None,
        token_service: TokenService | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_service = fraud_service or FraudService()
        self.token_service = token_service or TokenService()

    def build_user_response(self, user: dict[str, Any]) -> UserResponse:
        return build_user_response(user)

    async def register_user(
        self,
        payload: UserRegisterRequest,
        request: Request,
    ) -> AuthResponse:
        email = _normalize_email(str(payload.email))
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )

        now = utc_now()
        user_data = {
            "_id": generate_uuid(),
            "email": email,
            "password_hash": hash_password(payload.password),
            "full_name": payload.full_name,
            "role": UserRole.CUSTOMER.value,
            "plan": UserPlan.FREE.value,
            "is_active": True,
            "is_verified": False,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "linked_visitor_ids": [],
        }
        try:
            user = await self.user_repository.create_user(user_data)
        except DuplicateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            ) from exc

        linked_user = await self._link_request_visitor(
            user=user,
            request=request,
            audit_message="High-risk anonymous visitor linked during registration.",
        )
        user = linked_user or user
        return await self._build_auth_response(user, "Account created successfully.")

    async def login_user(
        self,
        payload: UserLoginRequest,
        request: Request,
    ) -> AuthResponse:
        email = _normalize_email(str(payload.email))
        user = await self.user_repository.find_by_email(email)
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        if not bool(user.get("is_active", False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled.",
            )

        updated_user = await self.user_repository.update_last_login(user["_id"])
        user = updated_user or user
        linked_user = await self._link_request_visitor(
            user=user,
            request=request,
            audit_message="High-risk anonymous visitor linked during login.",
        )
        user = linked_user or user
        return await self._build_auth_response(user, "Logged in successfully.")

    def get_me(self, current_user: dict[str, Any]) -> MeResponse:
        user = self.build_user_response(current_user)
        return MeResponse(
            id=user.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            plan=user.plan,
            is_active=user.is_active,
        )

    async def refresh(self, payload: RefreshTokenRequest) -> TokenRefreshResponse:
        access_token, refresh_token = await self.token_service.refresh_token_pair(
            payload.refresh_token
        )
        return TokenRefreshResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def logout(self, payload: LogoutRequest) -> dict[str, bool | str]:
        await self.token_service.revoke_refresh_token(payload.refresh_token)
        return {"success": True, "message": "Logged out successfully."}

    async def _build_auth_response(self, user: dict[str, Any], message: str) -> AuthResponse:
        access_token, refresh_token = await self.token_service.create_token_pair(user)
        return AuthResponse(
            success=True,
            message=message,
            user=self.build_user_response(user),
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def _link_request_visitor(
        self,
        user: dict[str, Any],
        request: Request,
        audit_message: str,
    ) -> dict[str, Any] | None:
        cookie_id = get_visitor_cookie(request.cookies)
        visitor = await self.visitor_repository.find_by_cookie_id(cookie_id)
        if visitor is None:
            return user

        linked_user = await self.user_repository.link_visitor(
            user_id=user["_id"],
            visitor_id=visitor["_id"],
        )
        await self.pdf_repository.attach_visitor_pdfs_to_user(
            visitor_id=visitor["_id"],
            user_id=user["_id"],
        )
        if int(visitor.get("risk_score", 0)) >= 70:
            await self.fraud_service.create_fraud_events(
                visitor_id=visitor["_id"],
                events=[
                    {
                        "event_type": FraudEventType.SUSPICIOUS_REIDENTIFICATION.value,
                        "severity": FraudSeverity.MEDIUM.value,
                        "risk_points": 0,
                        "message": audit_message,
                        "signals": {
                            "cookie_id": cookie_id,
                            "visitor_id": visitor["_id"],
                            "ip_address": normalize_ip(
                                request.client.host if request.client else ""
                            ),
                            "user_agent": request.headers.get("user-agent"),
                            "fingerprint_hash": visitor.get("primary_fingerprint_hash"),
                        },
                    }
                ],
            )
        return linked_user or user


def build_user_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=user["_id"],
        user_id=user["_id"],
        email=user.get("email", ""),
        full_name=user.get("full_name"),
        role=user.get("role", UserRole.CUSTOMER.value),
        plan=user.get("plan", UserPlan.FREE.value),
        is_active=bool(user.get("is_active", False)),
        is_verified=bool(user.get("is_verified", False)),
        created_at=user.get("created_at"),
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()
