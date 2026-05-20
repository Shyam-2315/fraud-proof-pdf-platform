from typing import Any

from app.repositories.admin_audit_repository import AdminAuditRepository
from app.utils.security import generate_uuid, utc_now


class AdminAuditService:
    def __init__(
        self,
        repository: AdminAuditRepository | None = None,
    ) -> None:
        self.repository = repository or AdminAuditRepository()

    async def log_access(
        self,
        action: str,
        target_type: str,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        audit_id = generate_uuid()
        return await self.repository.create(
            {
                "_id": audit_id,
                "id": audit_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "metadata": metadata or {},
                "created_at": utc_now(),
            }
        )

    async def list_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return await self.repository.list_logs(limit=limit)
