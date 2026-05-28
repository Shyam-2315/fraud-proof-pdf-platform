from typing import Any

from fastapi import Request

from app.config import get_settings
from app.core.public_config import get_visitor_cookie
from app.models.fraud import BlockedEntityType, FraudEventType, FraudSeverity
from app.models.fraud_event import (
    FraudEventType as AdminFraudEventType,
    FraudSeverity as AdminFraudSeverity,
)
from app.repositories.identity_repository import IdentityLinkRepository
from app.repositories.visitor_repository import VisitorRepository
from app.schemas.visitor import VisitorIdentifyRequest
from app.services.fraud_event_service import FraudEventService
from app.services.fraud_service import FraudService, calculate_risk_level
from app.fraud_engine.decision_engine import FraudEngineDecisionService
from app.fraud_engine.identity_graph import IdentityGraphService
from app.services.rate_limit_service import client_ip
from app.services.risk_scoring_service import RiskScoringService
from app.services.visitor_resolution import VisitorResolutionService
from app.utils.security import (
    generate_uuid,
    normalize_ip,
    safe_append_unique,
    utc_now,
)


class VisitorService:
    """
    Service that coordinates domain workflows and business rules.
    """
    def __init__(
        self,
        repository: VisitorRepository | None = None,
        fraud_service: FraudService | None = None,
        fraud_event_service: FraudEventService | None = None,
        identity_link_repository: IdentityLinkRepository | None = None,
        identity_graph_service: IdentityGraphService | None = None,
        risk_scoring_service: RiskScoringService | None = None,
        fraud_engine_decision_service: FraudEngineDecisionService | None = None,
    ) -> None:
        """
        Initialize the service with optional collaborators and runtime dependencies.
        
        Args:
            repository: The repository value used by this operation.
            fraud_service: The fraud service value used by this operation.
            fraud_event_service: The fraud event service value used by this operation.
            identity_link_repository: The identity link repository value used by this operation.
            identity_graph_service: The identity graph service value used by this operation.
            risk_scoring_service: The risk scoring service value used by this operation.
            fraud_engine_decision_service: The fraud engine decision service value used by this operation.
        
        Returns:
            None.
        """
        self.repository = repository or VisitorRepository()
        self.fraud_service = fraud_service or FraudService()
        self.fraud_event_service = fraud_event_service or FraudEventService()
        self.identity_link_repository = identity_link_repository or IdentityLinkRepository()
        self.identity_graph_service = identity_graph_service or IdentityGraphService(
            visitor_repository=self.repository,
            identity_link_repository=self.identity_link_repository,
        )
        self.risk_scoring_service = risk_scoring_service or RiskScoringService()
        self.fraud_engine_decision_service = fraud_engine_decision_service or FraudEngineDecisionService()
        self.visitor_resolution_service = VisitorResolutionService(
            repository=self.repository,
            fraud_event_service=self.fraud_event_service,
        )

    async def identify_visitor(
        self,
        request: Request,
        payload: VisitorIdentifyRequest,
    ) -> tuple[dict[str, Any], bool, str]:
        """
        Identify Visitor for the requested operation.
        
        Args:
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
            payload: Validated request payload for this operation.
        
        Returns:
            Operation result represented as `tuple[dict[str, Any], bool, str]`.
        """
        request_cookie_id = get_visitor_cookie(request.cookies)
        generated_cookie_id = request_cookie_id or generate_uuid()
        current_ip = normalize_ip(client_ip(request))
        current_user_agent = request.headers.get("user-agent", "")
        request_headers = dict(request.headers)
        now = utc_now()

        incoming_signals = _build_signals(
            cookie_id=request_cookie_id,
            local_storage_id=payload.local_storage_id,
            session_id=payload.session_id,
            fingerprint_hash=payload.fingerprint_hash,
            device_profile_hash=payload.device_profile_hash,
            canvas_hash=payload.canvas_hash,
            webgl_hash=payload.webgl_hash,
            ip_address=current_ip,
            user_agent=current_user_agent,
        )
        visitor = await self.identity_graph_service.find_strong_match(incoming_signals)
        weak_match = (
            None
            if visitor is not None
            else await self.identity_graph_service.find_related_match(incoming_signals)
        )

        if visitor is None:
            blocked_fingerprint = await self.fraud_service.is_fingerprint_blocked(
                payload.fingerprint_hash
            )
            is_blocked = blocked_fingerprint is not None
            risk_score = int(blocked_fingerprint.get("risk_score", 100)) if is_blocked else 0
            visitor_data = {
                "_id": generate_uuid(),
                "cookie_id": generated_cookie_id,
                "cookie_ids": safe_append_unique([], generated_cookie_id),
                "local_storage_ids": safe_append_unique([], payload.local_storage_id),
                "session_ids": safe_append_unique([], payload.session_id),
                "fingerprint_hashes": safe_append_unique([], payload.fingerprint_hash),
                "device_profile_hashes": safe_append_unique([], payload.device_profile_hash),
                "canvas_hashes": safe_append_unique([], payload.canvas_hash),
                "webgl_hashes": safe_append_unique([], payload.webgl_hash),
                "audio_hashes": safe_append_unique([], payload.audio_hash),
                "primary_fingerprint_hash": payload.fingerprint_hash,
                "ip_addresses": safe_append_unique([], current_ip),
                "ip_observations": [{"value": current_ip, "created_at": now}] if current_ip else [],
                "user_agents": safe_append_unique([], current_user_agent),
                "session_observations": [{"value": payload.session_id, "created_at": now}],
                "device_info": payload.device_info.model_dump(),
                "automation_signals": _automation_dict(payload),
                "free_usage_count": 0,
                "risk_score": risk_score,
                "risk_level": calculate_risk_level(risk_score),
                "is_blocked": is_blocked,
                "fraud_blocked": is_blocked,
                "block_reason": "FINGERPRINT_BLOCKED" if is_blocked else None,
                "created_at": now,
                "last_seen_at": now,
            }
            created_visitor = await self.repository.create_visitor(visitor_data)
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=created_visitor,
                event_type=AdminFraudEventType.VISITOR_IDENTIFIED.value,
                severity=AdminFraudSeverity.LOW.value,
                action="Anonymous visitor identified.",
                allowed=not is_blocked,
                reason=created_visitor.get("block_reason"),
                metadata={"is_new_visitor": True},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
            if weak_match is not None:
                weak_match_info = self.identity_graph_service.describe_match(
                    weak_match,
                    incoming_signals,
                )
                await self._create_identity_link(
                    request=request,
                    source_visitor_id=created_visitor["_id"],
                    target_visitor_id=weak_match["_id"],
                    link_type=weak_match_info["link_type"],
                    confidence=weak_match_info["confidence"],
                    reason=weak_match_info["reason"],
                    matched_signals=incoming_signals,
                )
            await self.risk_scoring_service.score_visitor(
                visitor=created_visitor,
                request=request,
                action_type="IDENTIFY",
                payload=payload,
                context={"automation_signals": _automation_dict(payload)},
            )
            await self.fraud_engine_decision_service.decide(
                visitor=created_visitor,
                request=request,
                action_type="VISITOR_IDENTIFY",
                payload=payload,
                context={"automation_signals": _automation_dict(payload)},
                normal_flow=True,
            )
            if is_blocked:
                await self.fraud_service.create_fraud_events(
                    created_visitor["_id"],
                    [
                        {
                            "event_type": FraudEventType.SUSPICIOUS_REIDENTIFICATION.value,
                            "severity": FraudSeverity.HIGH.value,
                            "risk_points": 40,
                            "message": "Blocked fingerprint attempted reidentification.",
                            "signals": _build_signals(
                                cookie_id=request_cookie_id,
                                local_storage_id=payload.local_storage_id,
                                session_id=payload.session_id,
                                fingerprint_hash=payload.fingerprint_hash,
                                ip_address=current_ip,
                                user_agent=current_user_agent,
                            ),
                        }
                    ],
                )
            return created_visitor, True, generated_cookie_id

        match_info = self.identity_graph_service.describe_match(visitor, incoming_signals)
        link_type = match_info["link_type"]
        confidence = match_info["confidence"]
        link_reason = match_info["reason"]
        is_new_session = payload.session_id not in visitor.get("session_ids", [])
        is_new_fingerprint = payload.fingerprint_hash not in visitor.get(
            "fingerprint_hashes",
            [],
        )
        risk_evaluation = self.fraud_service.evaluate_reidentification_risk(
            visitor=visitor,
            cookie_id=request_cookie_id,
            local_storage_id=payload.local_storage_id,
            session_id=payload.session_id,
            fingerprint_hash=payload.fingerprint_hash,
            ip_address=current_ip,
            user_agent=current_user_agent,
            headers=request_headers,
        )
        updated_risk_score = min(
            int(visitor.get("risk_score", 0)) + int(risk_evaluation["risk_points"]),
            100,
        )
        cookie_id = generated_cookie_id
        existing_cookie_ids = safe_append_unique(visitor.get("cookie_ids", []), visitor.get("cookie_id"))
        updated_cookie_ids = safe_append_unique(existing_cookie_ids, generated_cookie_id)
        cookie_missing_after_seen = not request_cookie_id and bool(existing_cookie_ids)
        cleared_cookie_same_fingerprint = (
            not request_cookie_id
            and payload.fingerprint_hash in visitor.get("fingerprint_hashes", [])
        )
        update_data = {
            "cookie_id": cookie_id,
            "cookie_ids": updated_cookie_ids,
            "local_storage_ids": safe_append_unique(
                visitor.get("local_storage_ids", []), payload.local_storage_id
            ),
            "session_ids": safe_append_unique(
                visitor.get("session_ids", []), payload.session_id
            ),
            "fingerprint_hashes": safe_append_unique(
                visitor.get("fingerprint_hashes", []), payload.fingerprint_hash
            ),
            "device_profile_hashes": safe_append_unique(
                visitor.get("device_profile_hashes", []), payload.device_profile_hash
            ),
            "canvas_hashes": safe_append_unique(
                visitor.get("canvas_hashes", []), payload.canvas_hash
            ),
            "webgl_hashes": safe_append_unique(
                visitor.get("webgl_hashes", []), payload.webgl_hash
            ),
            "audio_hashes": safe_append_unique(
                visitor.get("audio_hashes", []), payload.audio_hash
            ),
            "ip_addresses": safe_append_unique(
                visitor.get("ip_addresses", []), current_ip
            ),
            "ip_observations": safe_append_unique(
                visitor.get("ip_observations", []),
                {"value": current_ip, "created_at": now} if current_ip else None,
                max_items=50,
            ),
            "user_agents": safe_append_unique(
                visitor.get("user_agents", []), current_user_agent
            ),
            "session_observations": safe_append_unique(
                visitor.get("session_observations", []),
                {"value": payload.session_id, "created_at": now},
                max_items=50,
            ),
            "device_info": payload.device_info.model_dump(),
            "automation_signals": _automation_dict(payload),
            "risk_score": updated_risk_score,
            "risk_level": calculate_risk_level(updated_risk_score),
            "last_seen_at": now,
        }
        updated_visitor = await self.repository.update_visitor(
            visitor_id=visitor["_id"],
            update_data=update_data,
        )
        await self.fraud_service.create_fraud_events(
            visitor_id=visitor["_id"],
            events=risk_evaluation["events"],
        )
        final_visitor = updated_visitor or {**visitor, **update_data}
        await self._create_identity_link(
            request=request,
            source_visitor_id=final_visitor["_id"],
            target_visitor_id=visitor["_id"],
            link_type=link_type,
            confidence=confidence,
            reason=link_reason,
            matched_signals=incoming_signals,
        )
        risk_snapshot = await self.risk_scoring_service.score_visitor(
            visitor=final_visitor,
            request=request,
            action_type="IDENTIFY",
            payload=payload,
            context={
                "cookie_missing_after_seen": cookie_missing_after_seen,
                "cleared_cookie_same_fingerprint": cleared_cookie_same_fingerprint,
                "automation_signals": _automation_dict(payload),
            },
        )
        final_visitor = {
            **final_visitor,
            "risk_score": int(risk_snapshot["score"]),
            "risk_level": str(risk_snapshot["level"]),
            "risk_reasons": risk_snapshot.get("reasons", []),
        }
        await self.fraud_engine_decision_service.decide(
            visitor=final_visitor,
            request=request,
            action_type="VISITOR_IDENTIFY",
            payload=payload,
            context={
                "cookie_missing_after_seen": cookie_missing_after_seen,
                "cleared_cookie_same_fingerprint": cleared_cookie_same_fingerprint,
                "automation_signals": _automation_dict(payload),
            },
            normal_flow=True,
        )
        await self.fraud_event_service.create_from_request(
            request=request,
            visitor=final_visitor,
            event_type=AdminFraudEventType.VISITOR_IDENTIFIED.value,
            severity=AdminFraudSeverity.LOW.value,
            action="Anonymous visitor identified.",
            allowed=not bool(final_visitor.get("is_blocked", False)),
            reason=final_visitor.get("block_reason"),
            metadata={"is_new_visitor": False},
            local_storage_id=payload.local_storage_id,
            session_id=payload.session_id,
            fingerprint_hash=payload.fingerprint_hash,
        )
        if not request_cookie_id:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.COOKIE_MISSING.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="Existing visitor matched without cookie.",
                allowed=True,
                reason="Cookie missing on visitor identify.",
                metadata={"matched_visitor_id": visitor["_id"]},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
        if is_new_session:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.NEW_SESSION_LINKED.value,
                severity=AdminFraudSeverity.LOW.value,
                action="New session linked to existing visitor.",
                allowed=True,
                metadata={"session_id_count": len(final_visitor.get("session_ids", []))},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
        if is_new_fingerprint:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.NEW_FINGERPRINT_LINKED.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="New fingerprint linked to existing visitor.",
                allowed=True,
                metadata={
                    "fingerprint_hash_count": len(
                        final_visitor.get("fingerprint_hashes", [])
                    )
                },
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )
        if len(final_visitor.get("session_ids", [])) > 3:
            await self.fraud_event_service.create_from_request(
                request=request,
                visitor=final_visitor,
                event_type=AdminFraudEventType.MULTIPLE_SESSIONS_DETECTED.value,
                severity=AdminFraudSeverity.MEDIUM.value,
                action="Multiple sessions detected for visitor.",
                allowed=True,
                metadata={"session_id_count": len(final_visitor.get("session_ids", []))},
                local_storage_id=payload.local_storage_id,
                session_id=payload.session_id,
                fingerprint_hash=payload.fingerprint_hash,
            )

        if bool(risk_evaluation["should_block_fingerprint"]):
            await self.fraud_service.create_blocked_entity(
                entity_type=BlockedEntityType.FINGERPRINT.value,
                entity_value=payload.fingerprint_hash,
                reason="HIGH_RISK_FINGERPRINT",
                risk_score=updated_risk_score,
            )
            blocked_visitor = await self.repository.mark_visitor_blocked(
                visitor_id=visitor["_id"],
                reason="HIGH_RISK_FINGERPRINT",
            )
            if blocked_visitor is not None:
                updated_visitor = blocked_visitor
                final_visitor = blocked_visitor
                await self.fraud_event_service.create_from_request(
                    request=request,
                    visitor=blocked_visitor,
                    event_type=AdminFraudEventType.VISITOR_BLOCKED.value,
                    severity=AdminFraudSeverity.HIGH.value,
                    action="Visitor blocked.",
                    allowed=False,
                    reason="HIGH_RISK_FINGERPRINT",
                    metadata={"risk_score": updated_risk_score},
                    local_storage_id=payload.local_storage_id,
                    session_id=payload.session_id,
                    fingerprint_hash=payload.fingerprint_hash,
                )

        return final_visitor, False, cookie_id

    async def find_visitor_from_request(self, request: Request) -> dict[str, Any] | None:
        """
        Find visitor from request for the requested operation.
        
        Args:
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
        
        Returns:
            Matching record or value when available.
        """
        visitor, _ = await self.visitor_resolution_service.resolve(request)
        return visitor

    async def _create_identity_link(
        self,
        request: Request,
        source_visitor_id: str,
        target_visitor_id: str,
        link_type: str,
        confidence: int,
        reason: str,
        matched_signals: dict[str, Any],
    ) -> None:
        """
        Create Identity Link for the requested operation.
        
        Args:
            request: Incoming FastAPI request used to inspect headers, cookies, and client metadata.
            source_visitor_id: Unique source visitor identifier used by the operation.
            target_visitor_id: Unique target visitor identifier used by the operation.
            link_type: The link type value used by this operation.
            confidence: The confidence value used by this operation.
            reason: The reason value used by this operation.
            matched_signals: The matched signals value used by this operation.
        
        Returns:
            None.
        """
        link = await self.identity_link_repository.create_link(
            source_visitor_id=source_visitor_id,
            target_visitor_id=target_visitor_id,
            link_type=link_type,
            confidence=confidence,
            reason=reason,
            matched_signals=matched_signals,
        )
        await self.fraud_event_service.create_event(
            visitor_id=source_visitor_id,
            event_type=AdminFraudEventType.IDENTITY_LINK_CREATED.value,
            severity=(
                AdminFraudSeverity.HIGH.value
                if confidence >= 80
                else AdminFraudSeverity.MEDIUM.value
                if confidence >= 50
                else AdminFraudSeverity.LOW.value
            ),
            action="Identity graph link created.",
            allowed=True,
            reason=reason,
            risk_score=0,
            risk_level="LOW",
            fingerprint_hash=matched_signals.get("fingerprint_hash"),
            local_storage_id=matched_signals.get("local_storage_id"),
            session_id=matched_signals.get("session_id"),
            cookie_id=get_visitor_cookie(request.cookies),
            ip_address=matched_signals.get("ip_address"),
            user_agent=matched_signals.get("user_agent"),
            metadata={"identity_link": link},
        )


def build_usage_summary(visitor: dict[str, Any]) -> dict[str, int]:
    """
    Build usage summary data for the service workflow.
    
    Args:
        visitor: Visitor record involved in the operation.
    
    Returns:
        Constructed result for the requested operation.
    """
    settings = get_settings()
    free_usage_count = int(visitor.get("free_usage_count", 0))
    return {
        "free_usage_count": free_usage_count,
        "free_usage_limit": settings.FREE_USAGE_LIMIT,
        "remaining_free_uses": max(settings.FREE_USAGE_LIMIT - free_usage_count, 0),
    }


def _build_signals(
    cookie_id: str | None,
    local_storage_id: str | None,
    session_id: str | None,
    fingerprint_hash: str | None,
    device_profile_hash: str | None = None,
    canvas_hash: str | None = None,
    webgl_hash: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, str | None]:
    """
    Build Signals for the requested operation.
    
    Args:
        cookie_id: Unique cookie identifier used by the operation.
        local_storage_id: Unique local storage identifier used by the operation.
        session_id: Unique session identifier used by the operation.
        fingerprint_hash: Device fingerprint hash associated with the caller.
        device_profile_hash: Hash value representing device profile.
        canvas_hash: Hash value representing canvas.
        webgl_hash: Hash value representing webgl.
        ip_address: IP address being analyzed or persisted.
        user_agent: User-Agent string supplied by the client.
    
    Returns:
        Operation result represented as `dict[str, str | None]`.
    """
    return {
        "cookie_id": cookie_id,
        "local_storage_id": local_storage_id,
        "session_id": session_id,
        "fingerprint_hash": fingerprint_hash,
        "device_profile_hash": device_profile_hash,
        "canvas_hash": canvas_hash,
        "webgl_hash": webgl_hash,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }


def _automation_dict(payload: VisitorIdentifyRequest) -> dict[str, Any]:
    """
    Automation Dict for the requested operation.
    
    Args:
        payload: Validated request payload for this operation.
    
    Returns:
        Operation result represented as `dict[str, Any]`.
    """
    signals = payload.automation_signals
    if signals is None:
        return {}
    if hasattr(signals, "model_dump"):
        return signals.model_dump()
    return dict(signals)
