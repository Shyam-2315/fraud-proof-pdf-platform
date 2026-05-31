from datetime import UTC, datetime

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


def get_billing_period(month_key: str) -> tuple[datetime, datetime]:
    """
    Resolve the inclusive start and exclusive end for a monthly usage bucket.

    Args:
        month_key: Month bucket in ``YYYY-MM`` format.

    Returns:
        UTC-aware billing period boundaries for the month.
    """
    year_text, month_text = month_key.split("-", 1)
    year = int(year_text)
    month = int(month_text)
    period_start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        period_end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        period_end = datetime(year, month + 1, 1, tzinfo=UTC)
    return period_start, period_end


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
        billing_period_start, billing_period_end = get_billing_period(month_key)
        usage = await self.repository.get_or_create_usage(
            user_id=user["_id"],
            plan=plan,
            month_key=month_key,
            limit=limit,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
        )
        used = int(usage.get("pdf_count", 0))
        return {
            "plan": plan,
            "month_key": month_key,
            "billing_period_start": usage.get("billing_period_start", billing_period_start),
            "billing_period_end": usage.get("billing_period_end", billing_period_end),
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0),
            "requires_upgrade": used >= limit,
            "plan_limits": PLAN_LIMITS,
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
        month_key = get_month_key()
        billing_period_start, billing_period_end = get_billing_period(month_key)
        usage = await self.repository.increment_usage(
            user_id=user["_id"],
            plan=plan,
            month_key=month_key,
            limit=limit,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
        )
        used = int(usage.get("pdf_count", 0))
        return {
            "plan": plan,
            "month_key": usage["month_key"],
            "billing_period_start": usage.get("billing_period_start", billing_period_start),
            "billing_period_end": usage.get("billing_period_end", billing_period_end),
            "used": used,
            "limit": limit,
            "remaining": max(limit - used, 0),
            "requires_upgrade": used >= limit,
            "plan_limits": PLAN_LIMITS,
        }
