import hashlib
from typing import Any

from fastapi import Request

from app.core.auth import get_current_user_optional
from app.models.behavior import BehaviorEventType
from app.repositories.behavior_repository import BehaviorEventRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.behavior import BehaviorEventRequest
from app.services.visitor_resolution import VisitorResolutionService
from app.utils.security import generate_uuid, utc_now


class BehaviorService:
    """
    Service that coordinates domain workflows and business rules.
    """
    def __init__(
        self,
        repository: BehaviorEventRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
    ) -> None:
        """
        Initialize the service with optional collaborators and runtime dependencies.
        
        Args:
            repository: The repository value used by this operation.
            visitor_repository: The visitor repository value used by this operation.
        
        Returns:
            None.
        """
        self.repository = repository or BehaviorEventRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.visitor_resolution_service = VisitorResolutionService(repository=self.visitor_repository)

    async def record_event(
        self,
        request: Request,
        payload: BehaviorEventRequest,
    ) -> dict[str, Any]:
        """
        Record event data for the service workflow.
        
        Args:
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
            payload: Validated request payload for this operation.
        
        Returns:
            Outcome of the requested operation.
        """
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
        """
        Record internal event data for the service workflow.
        
        Args:
            visitor_id: Unique visitor identifier used by the operation.
            user_id: Unique user identifier used by the operation.
            event_type: Event type filter or value used by the operation.
            metadata: Additional metadata stored with the record or event.
        
        Returns:
            Outcome of the requested operation.
        """
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
        """
        Resolve Visitor for the requested operation.
        
        Args:
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
        
        Returns:
            Operation result represented as `dict[str, Any] | None`.
        """
        visitor, _ = await self.visitor_resolution_service.resolve(request)
        return visitor


def content_hash(content: str | None) -> str | None:
    """
    Build a stable content hash for the supplied input.
    
    Args:
        content: The content value used by this operation.
    
    Returns:
        Operation result represented as `str | None`.
    """
    if not content:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Safe Metadata for the requested operation.
    
    Args:
        metadata: Additional metadata stored with the record or event.
    
    Returns:
        Operation result represented as `dict[str, Any]`.
    """
    safe = dict(metadata)
    if "content" in safe:
        safe["content_hash"] = content_hash(str(safe.pop("content")))
    if "title" in safe:
        safe["title_length"] = len(str(safe["title"]))
        safe.pop("title", None)
    return safe
