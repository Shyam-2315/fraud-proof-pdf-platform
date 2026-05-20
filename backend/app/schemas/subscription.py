from pydantic import BaseModel


class AccountUsageResponse(BaseModel):
    plan: str
    month_key: str
    used: int
    limit: int
    remaining: int
    requires_upgrade: bool = False
