import hashlib
from typing import Any

from fastapi import Request

from app.core.auth import get_current_user_optional
from app.core.public_config import get_visitor_cookie
from app.models.behavior import BehaviorEventType
from app.repositories.behavior_repository import BehaviorEventRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.behavior import BehaviorEventRequest
from app.utils.security import generate_uuid, utc_now


class BehaviorService:
    def __init__(
        self,
        repository: BehaviorEventRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
    ) -> None:
        self.repository = repository or BehaviorEventRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()

    async def record_event(
        self,
        request: Request,
        payload: BehaviorEventRequest,
    ) -> dict[str, Any]:
        visitor = await self._resolve_visitor(request)
        current_user = await get_current_user_optional(request)
        metadata = _safe_metadata(payload.metadata)
        event_id = generate_uuid()
        return await self.repository.create(
            {
                "_id": event_id,
                "id": event_id,
                "visitor_id": visitor.get("_id") if visitor else None,
                "user_id": current_user.get("_id") if current_user else None,
                "event_type": payload.event_type,
                "metadata": metadata,
                "created_at": utc_now(),
            }
        )

    async def record_internal_event(
        self,
        visitor_id: str | None,
        user_id: str | None,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = generate_uuid()
        return await self.repository.create(
            {
                "_id": event_id,
                "id": event_id,
                "visitor_id": visitor_id,
                "user_id": user_id,
                "event_type": event_type,
                "metadata": _safe_metadata(metadata or {}),
                "created_at": utc_now(),
            }
        )

    async def _resolve_visitor(self, request: Request) -> dict[str, Any] | None:
        cookie_id = get_visitor_cookie(request.cookies)
        visitor = await self.visitor_repository.find_by_cookie_id(cookie_id)
        if visitor is not None:
            return visitor
        local_storage_id = request.headers.get("x-visitor-id")
        fingerprint_hash = request.headers.get("x-device-fingerprint")
        return (
            await self.visitor_repository.find_by_local_storage_id(local_storage_id)
            or await self.visitor_repository.find_by_fingerprint_hash(fingerprint_hash)
        )


def content_hash(content: str | None) -> str | None:
    if not content:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe = dict(metadata)
    if "content" in safe:
        safe["content_hash"] = content_hash(str(safe.pop("content")))
    if "title" in safe:
        safe["title_length"] = len(str(safe["title"]))
        safe.pop("title", None)
    return safe
