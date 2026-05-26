import secrets
from datetime import timedelta

from fastapi import HTTPException, status

from app.config import get_settings
from app.core.auth import create_access_token
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.utils.security import generate_uuid, utc_now


class TokenService:
    def __init__(
        self,
        refresh_token_repository: RefreshTokenRepository | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.settings = get_settings()
        self.refresh_token_repository = refresh_token_repository or RefreshTokenRepository()
        self.user_repository = user_repository or UserRepository()

    async def create_token_pair(self, user: dict) -> tuple[str, str]:
        access_token = create_access_token(
            subject=user["_id"],
            role=user.get("role"),
        )
        refresh_token = secrets.token_urlsafe(48)
        await self.refresh_token_repository.create_token(
            token_id=generate_uuid(),
            user_id=user["_id"],
            token=refresh_token,
            expires_at=utc_now() + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return access_token, refresh_token

    async def refresh_token_pair(self, refresh_token: str) -> tuple[str, str]:
        token_record = await self.refresh_token_repository.find_active_by_token(refresh_token)
        if token_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )
        user = await self.user_repository.find_by_id(token_record["user_id"])
        if user is None or not bool(user.get("is_active", False)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )
        if not bool(user.get("email_verified", user.get("is_verified", False))):
            await self.refresh_token_repository.revoke_by_id(token_record["_id"])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email to continue.",
            )
        await self.refresh_token_repository.revoke_by_id(token_record["_id"])
        return await self.create_token_pair(user)

    async def revoke_refresh_token(self, refresh_token: str | None) -> None:
        if refresh_token:
            await self.refresh_token_repository.revoke_by_token(refresh_token)
