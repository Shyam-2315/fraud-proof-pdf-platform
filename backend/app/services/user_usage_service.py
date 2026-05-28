from app.models.user import PLAN_LIMITS, UserPlan
from app.repositories.user_usage_repository import UserUsageRepository
from app.utils.security import utc_now


def get_month_key() -> str:
    """
    Return the current usage-month key used for monthly PDF quotas.

    Returns:
        Year-month string in ``YYYY-MM`` format.
    """
    return utc_now().strftime("%Y-%m")


def get_plan_limit(plan: str) -> int:
    """
    Resolve the monthly PDF limit for a subscription plan.

    Args:
        plan: User subscription plan name.

    Returns:
        Numeric monthly PDF limit for the plan, defaulting to the free plan.
    """
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[UserPlan.FREE.value])


class UserUsageService:
    """Manage monthly PDF usage counters for authenticated users."""

    def __init__(self, repository: UserUsageRepository | None = None) -> None:
        """
        Initialize the user usage service.

        Args:
            repository: Optional repository used for usage persistence.
        """
        self.repository = repository or UserUsageRepository()

    async def get_current_usage(self, user: dict) -> dict:
        """
        Return the current month's PDF usage summary for a user.

        Args:
            user: Authenticated user document whose usage should be loaded.

        Returns:
            Usage payload including plan, used count, remaining quota, and upgrade need.
        """
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
        """
        Increment monthly PDF usage after a successful authenticated generation.

        Args:
            user: Authenticated user document whose usage should be incremented.

        Returns:
            Updated usage payload after incrementing the monthly counter.
        """
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
