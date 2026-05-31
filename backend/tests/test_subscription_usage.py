import asyncio
from datetime import UTC, datetime

from app.models.user import UserPlan
from app.services import user_usage_service
from app.services.user_usage_service import (
    UserUsageService,
    get_billing_period,
    get_plan_limit,
)


class FakeUsageRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], dict] = {}

    async def get_or_create_usage(
        self,
        user_id: str,
        plan: str,
        month_key: str,
        limit: int,
        billing_period_start: datetime,
        billing_period_end: datetime,
    ) -> dict:
        key = (user_id, month_key)
        self.records.setdefault(
            key,
            {
                "user_id": user_id,
                "plan": plan,
                "month_key": month_key,
                "pdf_count": 0,
                "limit": limit,
                "billing_period_start": billing_period_start,
                "billing_period_end": billing_period_end,
            },
        )
        return self.records[key]

    async def increment_usage(
        self,
        user_id: str,
        plan: str,
        month_key: str,
        limit: int,
        billing_period_start: datetime,
        billing_period_end: datetime,
    ) -> dict:
        record = await self.get_or_create_usage(
            user_id=user_id,
            plan=plan,
            month_key=month_key,
            limit=limit,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
        )
        record["pdf_count"] += 1
        return record


def test_subscription_plan_limits_are_stable() -> None:
    assert get_plan_limit(UserPlan.FREE.value) == 5
    assert get_plan_limit(UserPlan.PRO.value) == 100
    assert get_plan_limit(UserPlan.BUSINESS.value) == 1000
    assert get_plan_limit("UNKNOWN") == 5


def test_billing_period_boundaries_are_monthly_utc() -> None:
    start, end = get_billing_period("2026-05")
    assert start == datetime(2026, 5, 1, tzinfo=UTC)
    assert end == datetime(2026, 6, 1, tzinfo=UTC)

    december_start, december_end = get_billing_period("2026-12")
    assert december_start == datetime(2026, 12, 1, tzinfo=UTC)
    assert december_end == datetime(2027, 1, 1, tzinfo=UTC)


def test_usage_resets_by_new_month_key(monkeypatch) -> None:
    repository = FakeUsageRepository()
    service = UserUsageService(repository=repository)
    user = {"_id": "user-1", "plan": UserPlan.FREE.value}

    monkeypatch.setattr(
        user_usage_service,
        "utc_now",
        lambda: datetime(2026, 5, 20, tzinfo=UTC),
    )
    may_usage = asyncio.run(service.increment_after_generation(user))
    assert may_usage["month_key"] == "2026-05"
    assert may_usage["used"] == 1

    monkeypatch.setattr(
        user_usage_service,
        "utc_now",
        lambda: datetime(2026, 6, 1, tzinfo=UTC),
    )
    june_usage = asyncio.run(service.get_current_usage(user))
    assert june_usage["month_key"] == "2026-06"
    assert june_usage["used"] == 0
    assert june_usage["remaining"] == 5
    assert june_usage["billing_period_start"] == datetime(2026, 6, 1, tzinfo=UTC)
    assert june_usage["billing_period_end"] == datetime(2026, 7, 1, tzinfo=UTC)
