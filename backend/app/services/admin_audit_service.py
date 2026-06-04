from typing import Any

from app.repositories.admin_audit_repository import AdminAuditRepository
from app.utils.security import generate_uuid, utc_now
from app.utils.sanitization import sanitize_log_value, sanitize_mapping


class AdminAuditService:
    """Create and list admin audit log entries."""

    def __init__(
        self,
        repository: AdminAuditRepository | None = None,
    ) -> None:
        """
        Initialize the admin audit service.

        Args:
            repository: Optional repository used for audit-log persistence.
        """
        self.repository = repository or AdminAuditRepository()

    async def log_access(
        self,
        action: str,
        target_type: str,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Persist an admin audit-log entry for a privileged action.

        Args:
            action: Audit action code being recorded.
            target_type: Target entity type the action affected.
            target_id: Optional identifier of the affected entity.
            metadata: Optional extra audit metadata for investigation.

        Returns:
            Stored audit log document.
        """
        audit_id = generate_uuid()
        return await self.repository.create(
            {
                "_id": audit_id,
                "id": audit_id,
                "action": sanitize_log_value(action),
                "target_type": sanitize_log_value(target_type),
                "target_id": sanitize_log_value(target_id),
                "metadata": sanitize_mapping(metadata or {}),
                "created_at": utc_now(),
            }
        )

    async def list_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Return recent admin audit-log entries.

        Args:
            limit: Maximum number of recent log entries to return.

        Returns:
            Recent audit log documents ordered by creation time.
        """
        return await self.repository.list_logs(limit=limit)
