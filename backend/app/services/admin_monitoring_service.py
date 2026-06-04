from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, status

from app.config import get_settings
from app.database import ping_mongo
from app.models.pdf import GENERATED_PDF_COLLECTION
from app.models.user import UserRole
from app.redis_client import ping_redis
from app.repositories.admin_repository import AdminRepository
from app.repositories.fraud_engine_repository import FraudEngineRepository
from app.repositories.pdf_repository import PDFRepository
from app.repositories.request_log_repository import RequestLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_usage_repository import UserUsageRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.admin_monitoring import (
    AdminMonitoringResponse,
    AdminRequestLogItem,
    AdminRequestLogListResponse,
    AdminUserActionResponse,
    AdminUserManagementItem,
    AdminUserManagementListResponse,
)
from app.services.user_usage_service import get_billing_period, get_month_key, get_plan_limit
from app.utils.security import utc_now
from app.utils.sanitization import sanitize_log_value, sanitize_plain_text


class AdminMonitoringService:
    """Read-only production monitoring and admin-management workflows."""

    def __init__(
        self,
        admin_repository: AdminRepository | None = None,
        visitor_repository: VisitorRepository | None = None,
        pdf_repository: PDFRepository | None = None,
        fraud_engine_repository: FraudEngineRepository | None = None,
        request_log_repository: RequestLogRepository | None = None,
        user_repository: UserRepository | None = None,
        usage_repository: UserUsageRepository | None = None,
    ) -> None:
        """
        Initialize the service with persistence collaborators.

        Args:
            admin_repository: Generic admin repository for cross-collection counts.
            visitor_repository: Visitor repository for anonymous-user metrics.
            pdf_repository: Generated PDF repository.
            fraud_engine_repository: Fraud decision repository.
            request_log_repository: Request log repository.
            user_repository: User account repository.
            usage_repository: Authenticated usage repository.
        """
        self.settings = get_settings()
        self.admin_repository = admin_repository or AdminRepository()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.pdf_repository = pdf_repository or PDFRepository()
        self.fraud_engine_repository = fraud_engine_repository or FraudEngineRepository()
        self.request_log_repository = request_log_repository or RequestLogRepository()
        self.user_repository = user_repository or UserRepository()
        self.usage_repository = usage_repository or UserUsageRepository()

    async def get_monitoring(self) -> AdminMonitoringResponse:
        """
        Return production health and core business metrics for admins.

        Returns:
            Monitoring metrics and readiness-like dependency checks.
        """
        mongodb_check = await _check_mongodb()
        redis_check = await _check_redis()
        storage_check = _directory_writable(self.settings.PDF_STORAGE_DIR)
        models_check = _directory_readable(self.settings.ML_MODELS_DIR)
        checks: dict[str, bool | str] = {
            "mongodb": mongodb_check,
            "redis": redis_check,
            "storage_writable": storage_check,
            "models_readable": models_check,
        }
        counts = await self._monitoring_counts() if mongodb_check is True else {}
        is_ready = all(value is True for value in checks.values())
        return AdminMonitoringResponse(
            total_users=int(counts.get("total_users", 0)),
            total_anonymous_visitors=int(counts.get("total_anonymous_visitors", 0)),
            total_pdfs_generated=int(counts.get("total_pdfs_generated", 0)),
            pdfs_generated_today=int(counts.get("pdfs_generated_today", 0)),
            blocked_visitors=int(counts.get("blocked_visitors", 0)),
            fraud_decisions_count=int(counts.get("fraud_decisions_count", 0)),
            mongodb_health=_health_text(mongodb_check),
            redis_health=_health_text(redis_check),
            storage_health=_health_text(storage_check),
            backend_readiness_status="ready" if is_ready else "not_ready",
            checks=checks,
        )

    async def get_request_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        method: str | None = None,
        status_code: int | None = None,
        path: str | None = None,
    ) -> AdminRequestLogListResponse:
        """
        Return recent sanitized API request logs for admin observability.

        Args:
            limit: Maximum number of logs to return.
            offset: Number of matching logs to skip.
            method: Optional HTTP method filter.
            status_code: Optional response status-code filter.
            path: Optional path substring filter.

        Returns:
            Paginated request-log response.
        """
        total = await self.request_log_repository.count_logs(
            method=method,
            status_code=status_code,
            path=sanitize_plain_text(path, max_length=256) if path else None,
        )
        logs = await self.request_log_repository.list_recent(
            limit=limit,
            offset=offset,
            method=method,
            status_code=status_code,
            path=sanitize_plain_text(path, max_length=256) if path else None,
        )
        return AdminRequestLogListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[_build_request_log_item(log) for log in logs],
        )

    async def get_users(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        plan: str | None = None,
        is_active: bool | None = None,
    ) -> AdminUserManagementListResponse:
        """
        Return users with current-period usage for the admin management page.

        Args:
            limit: Maximum number of users to return.
            offset: Number of matching users to skip.
            search: Optional email/name filter.
            plan: Optional subscription plan filter.
            is_active: Optional active/blocked filter.

        Returns:
            Paginated admin-safe user list.
        """
        total = await self.user_repository.count_for_admin(
            search=sanitize_plain_text(search, max_length=120) if search else None,
            plan=plan,
            is_active=is_active,
        )
        users = await self.user_repository.list_for_admin(
            limit=limit,
            offset=offset,
            search=sanitize_plain_text(search, max_length=120) if search else None,
            plan=plan,
            is_active=is_active,
        )
        items = [await self._build_user_item(user) for user in users]
        return AdminUserManagementListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=items,
        )

    async def set_user_active(self, user_id: str, is_active: bool) -> AdminUserActionResponse:
        """
        Block or unblock a non-admin user account.

        Args:
            user_id: Account identifier to update.
            is_active: New active state.

        Returns:
            Updated user row.

        Raises:
            HTTPException: If the account does not exist or blocking is unsafe.
        """
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        if not is_active and user.get("role") == UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin accounts cannot be blocked from this endpoint.",
            )
        updated = await self.user_repository.set_active(
            user_id=user_id,
            is_active=is_active,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return AdminUserActionResponse(
            success=True,
            user=await self._build_user_item(updated),
        )

    async def _monitoring_counts(self) -> dict[str, int]:
        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "total_users": await self.admin_repository.count_users(),
            "total_anonymous_visitors": await self.visitor_repository.count_visitors(),
            "total_pdfs_generated": await self.pdf_repository.count_pdfs(),
            "pdfs_generated_today": await self.admin_repository.count_documents(
                GENERATED_PDF_COLLECTION,
                {"created_at": {"$gte": today_start}},
            ),
            "blocked_visitors": await self.visitor_repository.count_blocked_visitors(),
            "fraud_decisions_count": await self.fraud_engine_repository.count_decisions(),
        }

    async def _build_user_item(self, user: dict[str, Any]) -> AdminUserManagementItem:
        month_key = get_month_key()
        period_start, period_end = get_billing_period(month_key)
        plan = str(user.get("plan") or "FREE")
        limit = get_plan_limit(plan)
        usage = await self.usage_repository.find_usage(
            user_id=str(user.get("_id", "")),
            month_key=month_key,
        )
        used = int((usage or {}).get("pdf_count", 0))
        return AdminUserManagementItem(
            user_id=str(user.get("_id", "")),
            email=str(user.get("email", "")),
            full_name=sanitize_plain_text(user.get("full_name"), max_length=100) if user.get("full_name") else None,
            role=sanitize_log_value(user.get("role", "")),
            plan=plan,
            is_active=bool(user.get("is_active", True)),
            is_verified=bool(user.get("is_verified", False)),
            email_verified=bool(user.get("email_verified", False)),
            used=used,
            limit=limit,
            remaining=max(limit - used, 0),
            month_key=month_key,
            billing_period_start=(usage or {}).get("billing_period_start", period_start),
            billing_period_end=(usage or {}).get("billing_period_end", period_end),
            linked_visitor_count=len(user.get("linked_visitor_ids", [])),
            created_at=_datetime_or_now(user.get("created_at")),
            last_login_at=user.get("last_login_at"),
        )


async def _check_mongodb() -> bool | str:
    try:
        await ping_mongo()
        return True
    except Exception as exc:
        return f"failed: {exc}"


async def _check_redis() -> bool | str:
    try:
        await ping_redis()
        return True
    except Exception as exc:
        return f"failed: {exc}"


def _directory_writable(path: str) -> bool | str:
    try:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=directory, prefix=".monitor-", delete=True):
            pass
        return True
    except Exception as exc:
        return f"failed: {exc}"


def _directory_readable(path: str) -> bool | str:
    try:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            return "failed: not a directory"
        next(directory.iterdir(), None)
        return True
    except StopIteration:
        return True
    except Exception as exc:
        return f"failed: {exc}"


def _health_text(value: bool | str) -> str:
    return "ok" if value is True else str(value)


def _build_request_log_item(log: dict[str, Any]) -> AdminRequestLogItem:
    fraud_score = log.get("fraud_score")
    return AdminRequestLogItem(
        request_id=sanitize_log_value(log.get("request_id", "")),
        method=sanitize_log_value(log.get("method", "")),
        path=sanitize_log_value(log.get("path", "")),
        status_code=int(log.get("status_code", 0)),
        duration_ms=float(log.get("duration_ms", 0)),
        client_ip=sanitize_log_value(log.get("client_ip")),
        block_reason=sanitize_log_value(log.get("block_reason")),
        fraud_score=float(fraud_score) if fraud_score is not None else None,
        created_at=_datetime_or_now(log.get("created_at")),
    )


def _datetime_or_now(value: Any) -> datetime:
    return value if isinstance(value, datetime) else utc_now()
