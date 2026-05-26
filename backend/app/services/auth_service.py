from typing import Any

from fastapi import HTTPException, Request, status
from pymongo.errors import DuplicateKeyError

from app.core.auth import hash_password, verify_password
from app.core.public_config import get_visitor_cookie
from app.models.fraud import FraudEventType, FraudSeverity
from app.models.fraud_event import FraudEventType as AdminFraudEventType
from app.models.fraud_event import FraudSeverity as AdminFraudSeverity
from app.models.identity import IdentityLinkType
from app.repositories.identity_repository import IdentityLinkRepository
from app.models.user import UserPlan, UserRole
from app.repositories.pdf_repository import PDFRepository
from app.repositories.user_repository import UserRepository
from app.repositories.visitor_repository import VisitorRepository
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
    UserResponse,
    VerificationResponse,
    VerifyEmailRequest,
)
from app.services.email_verification_service import EmailVerificationService
from app.services.fraud_event_service import FraudEventService
from app.services.fraud_service import FraudService
from app.fraud_engine.decision_engine import FraudEngineDecisionService
from app.services.rate_limit_service import client_ip
from app.services.token_service import TokenService
from app.utils.security import generate_uuid, normalize_ip, utc_now


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_service: FraudService | None = None,
        fraud_event_service: FraudEventService | None = None,
        identity_link_repository: IdentityLinkRepository | None = None,
        token_service: TokenService | None = None,
        fraud_engine_decision_service: FraudEngineDecisionService | None = None,
        email_verification_service: EmailVerificationService | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_service = fraud_service or FraudService()
        self.fraud_event_service = fraud_event_service or FraudEventService()
        self.identity_link_repository = identity_link_repository or IdentityLinkRepository()
        self.token_service = token_service or TokenService()
        self.fraud_engine_decision_service = fraud_engine_decision_service or FraudEngineDecisionService()
        self.email_verification_service = email_verification_service or EmailVerificationService(
            user_repository=self.user_repository
        )

    def build_user_response(self, user: dict[str, Any]) -> UserResponse:
        return build_user_response(user)

    async def register_user(
        self,
        payload: UserRegisterRequest,
        request: Request,
    ) -> RegisterResponse:
        email = self.email_verification_service.normalize_and_validate_email(str(payload.email))
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
            "email_verified": False,
            "email_verified_at": None,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "linked_visitor_ids": [],
            "fingerprint_hashes": [],
            "device_profile_hashes": [],
            "ip_addresses": [],
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
            is_registration=True,
        )
        user = linked_user or user
        await self.email_verification_service.create_and_send_code(user_id=user["_id"], email=email)
        return RegisterResponse(
            success=True,
            message="Account created. Please verify your email.",
            email=email,
        )

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
        if not _is_email_verified(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in.",
            )

        updated_user = await self.user_repository.update_last_login(user["_id"])
        user = updated_user or user
        linked_user = await self._link_request_visitor(
            user=user,
            request=request,
            audit_message="High-risk anonymous visitor linked during login.",
            is_registration=False,
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

    async def verify_email(self, payload: VerifyEmailRequest) -> VerificationResponse:
        await self.email_verification_service.verify_email(email=payload.email, code=payload.code)
        return VerificationResponse(
            success=True,
            message="Email verified successfully.",
        )

    async def resend_verification(
        self,
        payload: ResendVerificationRequest,
    ) -> VerificationResponse:
        await self.email_verification_service.resend_verification(email=payload.email)
        return VerificationResponse(
            success=True,
            message="If this email is registered, a verification code has been sent.",
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
        is_registration: bool,
    ) -> dict[str, Any] | None:
        cookie_id = get_visitor_cookie(request.cookies)
        visitor = await self.visitor_repository.find_by_cookie_id(cookie_id)
        if visitor is None:
            return user
        await self.fraud_engine_decision_service.decide(
            visitor=visitor,
            request=request,
            action_type="SIGNUP" if is_registration else "LOGIN",
            user=user,
            context={
                "account_created_after_free_limit": is_registration
                and (int(visitor.get("free_usage_count", 0)) >= 2 or bool(visitor.get("is_blocked", False)))
            },
            normal_flow=True,
        )

        linked_user = await self.user_repository.link_visitor(
            user_id=user["_id"],
            visitor_id=visitor["_id"],
        )
        linked_user = await self.user_repository.add_device_link(
            user_id=user["_id"],
            fingerprint_hash=visitor.get("primary_fingerprint_hash"),
            device_profile_hash=_last(visitor.get("device_profile_hashes", [])),
            ip_address=normalize_ip(client_ip(request)),
        ) or linked_user
        await self.identity_link_repository.create_link(
            source_visitor_id=visitor["_id"],
            target_visitor_id=user["_id"],
            link_type=IdentityLinkType.ACCOUNT_LINK.value,
            confidence=100,
            reason="Visitor linked to authenticated account.",
            matched_signals={
                "visitor_id": visitor["_id"],
                "user_id": user["_id"],
                "fingerprint_hash": visitor.get("primary_fingerprint_hash"),
                "device_profile_hash": _last(visitor.get("device_profile_hashes", [])),
                "ip_address": normalize_ip(client_ip(request)),
            },
        )
        await self.pdf_repository.attach_visitor_pdfs_to_user(
            visitor_id=visitor["_id"],
            user_id=user["_id"],
        )
        if is_registration:
            await self._emit_account_registration_events(
                request=request,
                visitor=visitor,
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
                                client_ip(request)
                            ),
                            "user_agent": request.headers.get("user-agent"),
                            "fingerprint_hash": visitor.get("primary_fingerprint_hash"),
                        },
                    }
                ],
            )
        return linked_user or user

    async def _emit_account_registration_events(
        self,
        request: Request,
        visitor: dict[str, Any],
        user_id: str,
    ) -> None:
        ip_address = normalize_ip(client_ip(request))
        fingerprint_hash = visitor.get("primary_fingerprint_hash")
        device_profile_hash = _last(visitor.get("device_profile_hashes", []))
        device_count = await self.user_repository.count_recent_by_device(
            fingerprint_hash=fingerprint_hash,
            device_profile_hash=device_profile_hash,
            hours=24,
        )
        ip_count = await self.user_repository.count_recent_by_ip(ip_address, hours=24)
        await self.fraud_event_service.create_event(
            visitor_id=visitor["_id"],
            event_type=AdminFraudEventType.ACCOUNT_CREATED_FROM_DEVICE.value,
            severity=AdminFraudSeverity.LOW.value,
            action="Account created from visitor device.",
            allowed=True,
            reason="Account linked to visitor device profile.",
            risk_score=int(visitor.get("risk_score", 0)),
            risk_level=str(visitor.get("risk_level", "LOW")),
            fingerprint_hash=fingerprint_hash,
            local_storage_id=_last(visitor.get("local_storage_ids", [])),
            session_id=_last(visitor.get("session_ids", [])),
            cookie_id=get_visitor_cookie(request.cookies),
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "user_id": user_id,
                "device_account_count_24h": device_count,
                "ip_account_count_24h": ip_count,
            },
        )
        if int(visitor.get("free_usage_count", 0)) >= 2 or bool(visitor.get("is_blocked", False)):
            await self.fraud_event_service.create_event(
                visitor_id=visitor["_id"],
                event_type=AdminFraudEventType.ACCOUNT_CREATED_AFTER_FREE_LIMIT.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="Account created after anonymous limit signal.",
                allowed=True,
                reason="Account was created after anonymous free usage was exhausted or blocked.",
                risk_score=int(visitor.get("risk_score", 0)),
                risk_level=str(visitor.get("risk_level", "LOW")),
                fingerprint_hash=fingerprint_hash,
                ip_address=ip_address,
                user_agent=request.headers.get("user-agent"),
                metadata={"user_id": user_id},
            )
        if device_count > 3:
            await self.fraud_event_service.create_event(
                visitor_id=visitor["_id"],
                event_type=AdminFraudEventType.MULTIPLE_ACCOUNTS_SAME_DEVICE.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="Multiple accounts from same device.",
                allowed=True,
                reason="More than 3 accounts were created from the same fingerprint/device in 24h.",
                risk_score=int(visitor.get("risk_score", 0)),
                risk_level=str(visitor.get("risk_level", "LOW")),
                fingerprint_hash=fingerprint_hash,
                ip_address=ip_address,
                metadata={"device_account_count_24h": device_count},
            )
            await self.fraud_event_service.create_event(
                visitor_id=visitor["_id"],
                event_type=AdminFraudEventType.ACCOUNT_FARMING_SUSPECTED.value,
                severity=AdminFraudSeverity.HIGH.value,
                action="Account farming suspected.",
                allowed=True,
                reason="Multiple accounts share a device signal.",
                risk_score=int(visitor.get("risk_score", 0)),
                risk_level=str(visitor.get("risk_level", "LOW")),
                fingerprint_hash=fingerprint_hash,
                ip_address=ip_address,
                metadata={"device_account_count_24h": device_count},
            )
        if ip_count > 3:
            await self.fraud_event_service.create_event(
                visitor_id=visitor["_id"],
                event_type=AdminFraudEventType.MULTIPLE_ACCOUNTS_SAME_IP.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="Multiple accounts from same IP.",
                allowed=True,
                reason="More than 3 accounts were created from the same IP in 24h.",
                risk_score=int(visitor.get("risk_score", 0)),
                risk_level=str(visitor.get("risk_level", "LOW")),
                fingerprint_hash=fingerprint_hash,
                ip_address=ip_address,
                metadata={"ip_account_count_24h": ip_count},
            )


def build_user_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=user["_id"],
        user_id=user["_id"],
        email=user.get("email", ""),
        full_name=user.get("full_name"),
        role=user.get("role", UserRole.CUSTOMER.value),
        plan=user.get("plan", UserPlan.FREE.value),
        is_active=bool(user.get("is_active", False)),
        is_verified=_is_email_verified(user),
        created_at=user.get("created_at"),
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _is_email_verified(user: dict[str, Any]) -> bool:
    return bool(user.get("email_verified", user.get("is_verified", False)))


def _last(values: list[Any]) -> Any:
    return values[-1] if values else None
