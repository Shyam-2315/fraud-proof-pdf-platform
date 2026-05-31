from datetime import datetime

from pydantic import BaseModel


class AccountUsageResponse(BaseModel):
    """
    Schema describing the account usage response payload.
    """
    plan: str
    month_key: str
    billing_period_start: datetime
    billing_period_end: datetime
    used: int
    limit: int
    remaining: int
    requires_upgrade: bool = False
    plan_limits: dict[str, int]
