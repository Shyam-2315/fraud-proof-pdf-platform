from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.utils.sanitization import contains_xss_payload, sanitize_mapping, sanitize_plain_text


class BehaviorEventRequest(BaseModel):
    """
    Schema describing the behavior event request payload.
    """
    event_type: str = Field(min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if contains_xss_payload(value):
            raise ValueError("Behavior event fields cannot contain unsafe HTML or script content.")
        sanitized = sanitize_plain_text(value, max_length=80)
        if not sanitized:
            raise ValueError("Behavior event fields cannot be empty.")
        return sanitized

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        for item in value.values():
            if isinstance(item, str) and contains_xss_payload(item):
                raise ValueError("Behavior event metadata contains unsafe HTML or script content.")
        return sanitize_mapping(value)



class BehaviorEventResponse(BaseModel):
    """
    Schema describing the behavior event response payload.
    """
    success: bool
