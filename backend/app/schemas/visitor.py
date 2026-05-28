from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeviceInfo(BaseModel):
    """
    Schema describing the device info payload.
    """
    model_config = ConfigDict(extra="allow")

    screen: str = ""
    timezone: str = ""
    language: str = ""
    platform: str = ""
    hardware_concurrency: int = Field(default=0, ge=0)
    device_memory: int = Field(default=0, ge=0)
    touch_support: int = Field(default=0, ge=0)


class AutomationSignals(BaseModel):
    """
    Schema describing the automation signals payload.
    """
    model_config = ConfigDict(extra="allow")

    webdriver: bool = False
    plugins_count: int | None = None
    cookies_enabled: bool | None = None
    local_storage_available: bool | None = None
    session_storage_available: bool | None = None


class VisitorIdentifyRequest(BaseModel):
    """
    Schema describing the visitor identify request payload.
    """
    local_storage_id: str = Field(min_length=1, max_length=256)
    session_id: str = Field(min_length=1, max_length=256)
    fingerprint_hash: str = Field(min_length=1, max_length=512)
    device_profile_hash: str | None = Field(default=None, max_length=512)
    canvas_hash: str | None = Field(default=None, max_length=512)
    webgl_hash: str | None = Field(default=None, max_length=512)
    audio_hash: str | None = Field(default=None, max_length=512)
    device_info: DeviceInfo
    automation_signals: AutomationSignals | dict[str, Any] | None = None


class VisitorIdentifyResponse(BaseModel):
    """
    Schema describing the visitor identify response payload.
    """
    success: bool
    visitor_id: str
    message: str


class VisitorStatusResponse(BaseModel):
    """
    Schema describing the visitor status response payload.
    """
    visitor_id: str
    used: int
    remaining: int
    free_limit: int
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int
    limit_reached: bool = False
    fraud_blocked: bool = False
    is_blocked: bool
    message: str | None = None
    requires_login: bool = False
