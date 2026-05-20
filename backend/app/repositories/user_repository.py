import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, ReturnDocument

from app.database import get_database
from app.models.user import USER_COLLECTION, UserPlan, UserRole
from app.utils.security import utc_now

logger = logging.getLogger(__name__)


class UserRepository:
    def get_collection(self) -> AsyncIOMotorCollection:
        return get_database()[USER_COLLECTION]

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        if not email:
            return None
        return await self.get_collection().find_one({"email": email})

    async def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        if not user_id:
            return None
        return await self.get_collection().find_one({"_id": user_id})

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        await self.get_collection().insert_one(user_data)
        return user_data

    async def update_plan(self, user_id: str, plan: str) -> dict[str, Any] | None:
        return await self.get_collection().find_one_and_update(
            {"_id": user_id},
            {"$set": {"plan": plan, "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )

    async def update_last_login(self, user_id: str) -> dict[str, Any] | None:
        now = utc_now()
        return await self.get_collection().find_one_and_update(
            {"_id": user_id},
            {"$set": {"last_login_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def link_visitor(
        self,
        user_id: str,
        visitor_id: str,
    ) -> dict[str, Any] | None:
        if not user_id or not visitor_id:
            return await self.find_by_id(user_id)
        return await self.get_collection().find_one_and_update(
            {"_id": user_id},
            {
                "$addToSet": {"linked_visitor_ids": visitor_id},
                "$set": {"updated_at": utc_now()},
            },
            return_document=ReturnDocument.AFTER,
        )


async def ensure_user_indexes() -> None:
    collection = UserRepository().get_collection()
    await collection.create_index(
        [("email", ASCENDING)],
        name="idx_users_email_unique",
        unique=True,
    )
    await collection.create_index(
        [("created_at", ASCENDING)],
        name="idx_users_created_at",
    )
    await collection.create_index(
        [("linked_visitor_ids", ASCENDING)],
        name="idx_users_linked_visitor_ids",
    )
    await collection.create_index(
        [("role", ASCENDING)],
        name="idx_users_role",
    )
    logger.info("Ensured user collection indexes")


async def seed_default_admin() -> None:
    from app.config import get_settings
    from app.core.auth import hash_password
    from app.utils.security import generate_uuid

    settings = get_settings()
    if not settings.DEFAULT_ADMIN_EMAIL or not settings.DEFAULT_ADMIN_PASSWORD:
        return

    repository = UserRepository()
    email = settings.DEFAULT_ADMIN_EMAIL.strip().lower()
    if await repository.find_by_email(email):
        return

    now = utc_now()
    await repository.create_user(
        {
            "_id": generate_uuid(),
            "email": email,
            "full_name": settings.DEFAULT_ADMIN_NAME,
            "password_hash": hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            "role": UserRole.ADMIN.value,
            "plan": UserPlan.BUSINESS.value,
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "linked_visitor_ids": [],
        }
    )
    logger.info("Seeded default admin user email=%s", email)
