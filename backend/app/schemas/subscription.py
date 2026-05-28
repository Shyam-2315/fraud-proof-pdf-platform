from pydantic import BaseModel


class AccountUsageResponse(BaseModel):
    """
    Schema describing the account usage response payload.
    """
    plan: str
    month_key: str
    used: int
    limit: int
    remaining: int
    requires_upgrade: bool = False
