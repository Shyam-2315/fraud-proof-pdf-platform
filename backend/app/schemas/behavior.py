from typing import Any

from pydantic import BaseModel, Field


class BehaviorEventRequest(BaseModel):
    """
    Schema describing the behavior event request payload.
    """
    event_type: str = Field(min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BehaviorEventResponse(BaseModel):
    """
    Schema describing the behavior event response payload.
    """
    success: bool
