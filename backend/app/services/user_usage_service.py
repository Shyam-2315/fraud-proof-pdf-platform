from app.models.user import PLAN_LIMITS, UserPlan
from app.repositories.user_usage_repository import UserUsageRepository
from app.utils.security import utc_now


def get_month_key() -> str:
    return utc_now().strftime("%Y-%m")


def get_plan_limit(plan: str) -> int:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[UserPlan.FREE.value])


class UserUsageService:
    def __init__(self, repository: UserUsageRepository | None = None) -> None:
        self.repository = repository or UserUsageRepository()

    async def get_current_usage(self, user: dict) -> dict:
        plan = str(user.get("plan") or UserPlan.FREE.value)
        limit = get_plan_limit(plan)
        month_key = get_month_key()
        usage = await self.repository.get_or_create_usage(
            user_id=user["_id"],
            plan=plan,
            month_key=month_key,
            limit=limit,
        )
        used = int(usage.get("pdf_count", 0))
        return {
            "plan": plan,
            "month_key": month_key,
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0),
            "requires_upgrade": used >= limit,
        }

    async def increment_after_generation(self, user: dict) -> dict:
        plan = str(user.get("plan") or UserPlan.FREE.value)
        limit = get_plan_limit(plan)
        usage = await self.repository.increment_usage(
            user_id=user["_id"],
            plan=plan,
            month_key=get_month_key(),
            limit=limit,
        )
        used = int(usage.get("pdf_count", 0))
        return {
            "plan": plan,
            "month_key": usage["month_key"],
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0),
            "requires_upgrade": used >= limit,
        }
