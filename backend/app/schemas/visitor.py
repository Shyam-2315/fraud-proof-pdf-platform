from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    screen: str
    timezone: str
    language: str
    platform: str
    hardware_concurrency: int = Field(ge=0)
    device_memory: int = Field(ge=0)
    touch_support: int = Field(ge=0)


class VisitorIdentifyRequest(BaseModel):
    local_storage_id: str = Field(min_length=1, max_length=256)
    session_id: str = Field(min_length=1, max_length=256)
    fingerprint_hash: str = Field(min_length=1, max_length=512)
    device_info: DeviceInfo


class VisitorIdentifyResponse(BaseModel):
    visitor_id: str
    is_new_visitor: bool
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int
    risk_score: int
    risk_level: str
    is_blocked: bool
    message: str


class TrackedSignals(BaseModel):
    local_storage_ids: int
    session_ids: int
    fingerprint_hashes: int
    ip_addresses: int
    user_agents: int


class VisitorStatusResponse(BaseModel):
    visitor_id: str
    free_usage_count: int
    free_usage_limit: int
    remaining_free_uses: int
    risk_score: int
    risk_level: str
    is_blocked: bool
    block_reason: str | None
    tracked_signals: TrackedSignals
