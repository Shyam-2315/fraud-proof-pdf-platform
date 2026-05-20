import asyncio
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.config import get_settings
from app.database import ping_mongo
from app.models.fraud import BLOCKED_ENTITIES_COLLECTION, FRAUD_EVENTS_COLLECTION
from app.models.pdf import GENERATED_PDF_COLLECTION
from app.models.user import USER_COLLECTION
from app.models.visitor import VISITOR_COLLECTION
from app.redis_client import ping_redis
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import (
    AdminBlockedEntityItem,
    AdminDashboardResponse,
    AdminListResponse,
    AdminPDFListItem,
    AdminSystemHealthResponse,
    AdminUserListItem,
    AdminVisitorDetailResponse,
    AdminVisitorListItem,
)
from app.services.visitor_service import build_usage_summary
from app.utils.security import utc_now


class AdminService:
    def __init__(self, repository: AdminRepository | None = None) -> None:
        self.repository = repository or AdminRepository()
        self.settings = get_settings()

    async def get_dashboard(self) -> AdminDashboardResponse:
        (
            total_visitors,
            total_users,
            total_pdfs,
            anonymous_pdfs,
            authenticated_pdfs,
            blocked_visitors,
            high_risk_visitors,
            total_fraud_events,
            blocked_entities,
            conversion_count,
            recent_visitors,
            recent_users,
            recent_pdfs,
            recent_fraud_events,
        ) = await asyncio.gather(
            self.repository.count_visitors(),
            self.repository.count_users(),
            self.repository.count_pdfs(),
            self.repository.count_anonymous_pdfs(),
            self.repository.count_authenticated_pdfs(),
            self.repository.count_blocked_visitors(),
            self.repository.count_high_risk_visitors(),
            self.repository.count_fraud_events(),
            self.repository.count_blocked_entities(),
            self.repository.count_converted_users(),
            self.repository.list_recent_visitors(),
            self.repository.list_recent_users(),
            self.repository.list_recent_pdfs(),
            self.repository.list_recent_fraud_events(),
        )
        conversion_rate = (
            round((conversion_count / total_visitors) * 100, 2)
            if total_visitors > 0
            else 0.0
        )
        return AdminDashboardResponse(
            total_visitors=total_visitors,
            total_users=total_users,
            total_pdfs=total_pdfs,
            anonymous_pdfs=anonymous_pdfs,
            authenticated_pdfs=authenticated_pdfs,
            blocked_visitors=blocked_visitors,
            high_risk_visitors=high_risk_visitors,
            total_fraud_events=total_fraud_events,
            blocked_entities=blocked_entities,
            conversion_count=conversion_count,
            conversion_rate_percent=conversion_rate,
            recent_visitors=[
                _build_visitor_list_item(visitor).model_dump()
                for visitor in recent_visitors
            ],
            recent_users=[
                await self._build_user_list_item(user) for user in recent_users
            ],
            recent_pdfs=[_build_pdf_list_item(pdf).model_dump() for pdf in recent_pdfs],
            recent_fraud_events=[
                _build_fraud_event_item(event) for event in recent_fraud_events
            ],
        )

    async def get_visitors(
        self,
        limit: int,
        offset: int,
        risk_level: str | None,
        is_blocked: bool | None,
    ) -> AdminListResponse:
        filter_query = _remove_none(
            {"risk_level": risk_level, "is_blocked": is_blocked}
        )
        total, visitors = await asyncio.gather(
            self.repository.count_documents(VISITOR_COLLECTION, filter_query),
            self.repository.list_visitors(
                limit=limit,
                offset=offset,
                risk_level=risk_level,
                is_blocked=is_blocked,
            ),
        )
        return AdminListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[
                _build_visitor_list_item(visitor).model_dump()
                for visitor in visitors
            ],
        )

    async def get_visitor_detail(
        self,
        visitor_id: str,
    ) -> AdminVisitorDetailResponse:
        visitor = await self.repository.get_document_by_id(
            VISITOR_COLLECTION,
            visitor_id,
        )
        if visitor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visitor not found.",
            )

        generated_pdfs, fraud_events, linked_users = await asyncio.gather(
            self.repository.list_documents(
                GENERATED_PDF_COLLECTION,
                {"visitor_id": visitor_id},
                limit=100,
            ),
            self.repository.list_documents(
                FRAUD_EVENTS_COLLECTION,
                {"visitor_id": visitor_id},
                limit=100,
            ),
            self.repository.list_documents(
                USER_COLLECTION,
                {"linked_visitor_ids": visitor_id},
                limit=100,
            ),
        )
        usage_summary = build_usage_summary(visitor)
        return AdminVisitorDetailResponse(
            visitor_id=str(visitor.get("_id", "")),
            cookie_id=visitor.get("cookie_id"),
            local_storage_ids=_string_list(visitor.get("local_storage_ids", [])),
            session_ids=_string_list(visitor.get("session_ids", [])),
            fingerprint_hashes=_string_list(visitor.get("fingerprint_hashes", [])),
            primary_fingerprint_hash=visitor.get("primary_fingerprint_hash"),
            ip_addresses=_string_list(visitor.get("ip_addresses", [])),
            user_agents=_string_list(visitor.get("user_agents", [])),
            device_info=dict(visitor.get("device_info", {})),
            **usage_summary,
            risk_score=int(visitor.get("risk_score", 0)),
            risk_level=str(visitor.get("risk_level", "LOW")),
            is_blocked=bool(visitor.get("is_blocked", False)),
            block_reason=visitor.get("block_reason"),
            created_at=_datetime_or_now(visitor.get("created_at")),
            last_seen_at=_datetime_or_now(visitor.get("last_seen_at")),
            generated_pdfs=[
                _build_pdf_list_item(pdf).model_dump() for pdf in generated_pdfs
            ],
            fraud_events=[_build_fraud_event_item(event) for event in fraud_events],
            linked_users=[
                await self._build_user_list_item(user) for user in linked_users
            ],
        )

    async def get_users(self, limit: int, offset: int) -> AdminListResponse:
        total, users = await asyncio.gather(
            self.repository.count_documents(USER_COLLECTION),
            self.repository.list_users(limit=limit, offset=offset),
        )
        return AdminListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[await self._build_user_list_item(user) for user in users],
        )

    async def get_pdfs(
        self,
        limit: int,
        offset: int,
        generation_type: str | None,
    ) -> AdminListResponse:
        filter_query = _remove_none({"generation_type": generation_type})
        total, pdfs = await asyncio.gather(
            self.repository.count_documents(GENERATED_PDF_COLLECTION, filter_query),
            self.repository.list_pdfs(
                limit=limit,
                offset=offset,
                generation_type=generation_type,
            ),
        )
        return AdminListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[_build_pdf_list_item(pdf).model_dump() for pdf in pdfs],
        )

    async def get_fraud_events(
        self,
        limit: int,
        offset: int,
        severity: str | None,
        event_type: str | None,
    ) -> AdminListResponse:
        filter_query = _remove_none({"severity": severity, "event_type": event_type})
        total, events = await asyncio.gather(
            self.repository.count_documents(FRAUD_EVENTS_COLLECTION, filter_query),
            self.repository.list_fraud_events(
                limit=limit,
                offset=offset,
                severity=severity,
                event_type=event_type,
            ),
        )
        return AdminListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[_build_fraud_event_item(event) for event in events],
        )

    async def get_blocked_entities(
        self,
        limit: int,
        offset: int,
        entity_type: str | None,
        is_active: bool | None,
    ) -> AdminListResponse:
        filter_query = _remove_none(
            {"entity_type": entity_type, "is_active": is_active}
        )
        total, blocked_entities = await asyncio.gather(
            self.repository.count_documents(BLOCKED_ENTITIES_COLLECTION, filter_query),
            self.repository.list_blocked_entities(
                limit=limit,
                offset=offset,
                entity_type=entity_type,
                is_active=is_active,
            ),
        )
        return AdminListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[
                _build_blocked_entity_item(entity).model_dump()
                for entity in blocked_entities
            ],
        )

    async def get_system_health(self) -> AdminSystemHealthResponse:
        database_status, redis_status = await asyncio.gather(
            _ping_database(),
            _ping_cache(),
        )
        collections = {
            "visitors": await self._safe_count_collection(VISITOR_COLLECTION),
            "users": await self._safe_count_collection(USER_COLLECTION),
            "generated_pdfs": await self._safe_count_collection(
                GENERATED_PDF_COLLECTION
            ),
            "fraud_events": await self._safe_count_collection(FRAUD_EVENTS_COLLECTION),
            "blocked_entities": await self._safe_count_collection(
                BLOCKED_ENTITIES_COLLECTION
            ),
        }
        status_value = (
            "ok"
            if database_status == "ok" and redis_status == "ok"
            else "degraded"
        )
        return AdminSystemHealthResponse(
            status=status_value,
            service=self.settings.APP_NAME,
            database=database_status,
            redis=redis_status,
            collections=collections,
            ports={
                "backend": 8025,
                "future_frontend": 3025,
                "mongodb_host": 27225,
                "redis_host": 6385,
            },
        )

    async def _build_user_list_item(self, user: dict[str, Any]) -> dict[str, Any]:
        user_id = str(user.get("_id", ""))
        pdf_count = await self.repository.count_documents(
            GENERATED_PDF_COLLECTION,
            {"user_id": user_id},
        )
        return AdminUserListItem(
            user_id=user_id,
            email=str(user.get("email", "")),
            full_name=user.get("full_name"),
            is_active=bool(user.get("is_active", False)),
            is_verified=bool(user.get("is_verified", False)),
            linked_visitor_count=len(user.get("linked_visitor_ids", [])),
            pdf_count=pdf_count,
            created_at=_datetime_or_now(user.get("created_at")),
            last_login_at=user.get("last_login_at"),
        ).model_dump()

    async def _safe_count_collection(self, collection_name: str) -> int:
        try:
            return await self.repository.count_documents(collection_name)
        except Exception:
            return -1


def _build_visitor_list_item(visitor: dict[str, Any]) -> AdminVisitorListItem:
    usage_summary = build_usage_summary(visitor)
    return AdminVisitorListItem(
        visitor_id=str(visitor.get("_id", "")),
        **usage_summary,
        risk_score=int(visitor.get("risk_score", 0)),
        risk_level=str(visitor.get("risk_level", "LOW")),
        is_blocked=bool(visitor.get("is_blocked", False)),
        block_reason=visitor.get("block_reason"),
        ip_count=len(visitor.get("ip_addresses", [])),
        session_count=len(visitor.get("session_ids", [])),
        fingerprint_count=len(visitor.get("fingerprint_hashes", [])),
        user_agent_count=len(visitor.get("user_agents", [])),
        created_at=_datetime_or_now(visitor.get("created_at")),
        last_seen_at=_datetime_or_now(visitor.get("last_seen_at")),
    )


def _build_pdf_list_item(pdf: dict[str, Any]) -> AdminPDFListItem:
    return AdminPDFListItem(
        pdf_id=str(pdf.get("_id", "")),
        visitor_id=pdf.get("visitor_id"),
        user_id=pdf.get("user_id"),
        title=str(pdf.get("title", "")),
        file_name=str(pdf.get("file_name", "")),
        file_path=str(pdf.get("file_path", "")),
        generation_type=str(pdf.get("generation_type", "")),
        ip_address=pdf.get("ip_address"),
        fingerprint_hash=pdf.get("fingerprint_hash"),
        created_at=_datetime_or_now(pdf.get("created_at")),
    )


def _build_fraud_event_item(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(event.get("_id", "")),
        "visitor_id": event.get("visitor_id"),
        "event_type": str(event.get("event_type", "")),
        "severity": str(event.get("severity", "")),
        "risk_points": int(event.get("risk_points", 0)),
        "message": str(event.get("message", "")),
        "signals": dict(event.get("signals", {})),
        "created_at": _datetime_or_now(event.get("created_at")),
    }


def _build_blocked_entity_item(entity: dict[str, Any]) -> AdminBlockedEntityItem:
    return AdminBlockedEntityItem(
        entity_id=str(entity.get("_id", "")),
        entity_type=str(entity.get("entity_type", "")),
        entity_value=str(entity.get("entity_value", "")),
        reason=str(entity.get("reason", "")),
        risk_score=int(entity.get("risk_score", 0)),
        is_active=bool(entity.get("is_active", False)),
        created_at=_datetime_or_now(entity.get("created_at")),
        expires_at=entity.get("expires_at"),
    )


async def _ping_database() -> str:
    try:
        await ping_mongo()
    except Exception as exc:
        return f"error: {exc}"
    return "ok"


async def _ping_cache() -> str:
    try:
        await ping_redis()
    except Exception as exc:
        return f"error: {exc}"
    return "ok"


def _datetime_or_now(value: Any) -> datetime:
    return value if isinstance(value, datetime) else utc_now()


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _remove_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
