from typing import Any

from fastapi import Request

from app.config import get_settings
from app.fraud_engine.feature_builder import FeatureBuilder
from app.fraud_engine.ml_model import FraudMLModel
from app.fraud_engine.rule_engine import RuleEngine
from app.fraud_engine.schemas import FraudDecisionResult, risk_level_for_score
from app.fraud_engine.weak_labeler import weak_label_from_rule_score
from app.models.fraud_event import FraudEventType, FraudSeverity
from app.repositories.fraud_engine_repository import FraudEngineRepository
from app.repositories.risk_repository import RiskScoreSnapshotRepository
from app.repositories.visitor_repository import VisitorRepository
from app.services.fraud_event_service import FraudEventService
from app.utils.security import generate_uuid, utc_now


class FraudEngineDecisionService:
    def __init__(
        self,
        repository: FraudEngineRepository | None = None,
        feature_builder: FeatureBuilder | None = None,
        rule_engine: RuleEngine | None = None,
        visitor_repository: VisitorRepository | None = None,
        snapshot_repository: RiskScoreSnapshotRepository | None = None,
        fraud_event_service: FraudEventService | None = None,
        ml_model: Any | None = None,
    ) -> None:
        self.settings = get_settings()
        self.repository = repository or FraudEngineRepository()
        self.feature_builder = feature_builder or FeatureBuilder(repository=self.repository)
        self.rule_engine = rule_engine or RuleEngine()
        self.ml_model = ml_model or FraudMLModel()
        self.visitor_repository = visitor_repository or VisitorRepository()
        self.snapshot_repository = snapshot_repository or RiskScoreSnapshotRepository()
        self.fraud_event_service = fraud_event_service or FraudEventService()

    async def decide(
        self,
        visitor: dict[str, Any],
        request: Request | None,
        action_type: str,
        user: dict[str, Any] | None = None,
        payload: Any | None = None,
        context: dict[str, Any] | None = None,
        normal_flow: bool = False,
    ) -> FraudDecisionResult:
        features = await self.feature_builder.build(
            visitor=visitor,
            request=request,
            action_type=action_type,
            user=user,
            payload=payload,
            context=context,
            store_snapshot=True,
        )
        rule_result = self.rule_engine.evaluate(features)
        ml_result = self.ml_model.predict(features)
        final_score = _final_score(rule_result.rule_score, ml_result, features)
        final_score = max(0, min(final_score, 100))
        risk_level = risk_level_for_score(final_score)
        decision = _decision_for_score(final_score, user is not None)
        if user is None and int(visitor.get("free_usage_count", 0)) >= self.settings.FREE_USAGE_LIMIT:
            decision = "REQUIRE_LOGIN"

        decision_id = generate_uuid()
        result = FraudDecisionResult(
            fraud_probability=ml_result.fraud_probability,
            anomaly_score=ml_result.anomaly_score,
            rule_score=rule_result.rule_score,
            final_risk_score=final_score,
            risk_level=risk_level,
            decision=decision,
            reasons=rule_result.reason_dicts(),
            model_version=ml_result.model_version,
            decision_id=decision_id,
        )
        now = utc_now()
        await self.repository.create_decision(
            {
                "_id": decision_id,
                "id": decision_id,
                "visitor_id": visitor.get("_id"),
                "user_id": user.get("_id") if user else None,
                "action_type": action_type,
                "rule_score": rule_result.rule_score,
                "fraud_probability": ml_result.fraud_probability,
                "anomaly_score": ml_result.anomaly_score,
                "final_risk_score": final_score,
                "risk_level": risk_level,
                "decision": decision,
                "reasons": rule_result.reason_dicts(),
                "model_version": ml_result.model_version,
                "created_at": now,
            }
        )
        snapshot_id = generate_uuid()
        await self.snapshot_repository.create(
            {
                "_id": snapshot_id,
                "id": snapshot_id,
                "visitor_id": visitor.get("_id"),
                "user_id": user.get("_id") if user else None,
                "score": final_score,
                "level": risk_level,
                "reasons": rule_result.reason_dicts(),
                "signals": {
                    "features": features,
                    "fraud_probability": ml_result.fraud_probability,
                    "anomaly_score": ml_result.anomaly_score,
                    "model_version": ml_result.model_version,
                },
                "created_at": now,
            }
        )
        if visitor.get("_id"):
            await self.visitor_repository.update_visitor(
                visitor_id=visitor["_id"],
                update_data={
                    "risk_score": final_score,
                    "risk_level": risk_level,
                    "risk_reasons": rule_result.reason_dicts(),
                    "last_risk_signals": {
                        "decision_id": decision_id,
                        "model_version": ml_result.model_version,
                    },
                    "last_seen_at": now,
                },
            )
        weak_label = weak_label_from_rule_score(
            rule_result.rule_score,
            features,
            normal_flow=normal_flow or decision == "ALLOW",
        )
        training_event_id = generate_uuid()
        await self.repository.create_training_event(
            {
                "_id": training_event_id,
                "id": training_event_id,
                "visitor_id": visitor.get("_id"),
                "user_id": user.get("_id") if user else None,
                "action_type": action_type,
                "features": features,
                "rule_score": rule_result.rule_score,
                "rule_reasons": rule_result.reason_dicts(),
                "ml_score_at_time": ml_result.fraud_probability,
                "anomaly_score_at_time": ml_result.anomaly_score,
                "decision_at_time": decision,
                "outcome_label": weak_label["outcome_label"],
                "label_source": weak_label["label_source"],
                "label_confidence": weak_label["label_confidence"],
                "created_at": now,
            }
        )
        await self.fraud_event_service.create_event(
            visitor_id=visitor.get("_id"),
            event_type=FraudEventType.RISK_SCORE_UPDATED.value,
            severity=_severity_for_level(risk_level),
            action="Fraud engine decision evaluated.",
            allowed=decision in {"ALLOW", "ALLOW_LOG"},
            reason="; ".join(reason["message"] for reason in rule_result.reason_dicts()) or "No elevated risk signals.",
            risk_score=final_score,
            risk_level=risk_level,
            fingerprint_hash=visitor.get("primary_fingerprint_hash"),
            local_storage_id=_last(visitor.get("local_storage_ids", [])),
            session_id=_last(visitor.get("session_ids", [])),
            cookie_id=visitor.get("cookie_id"),
            metadata=result.as_dict(),
        )
        return result


def _decision_for_score(score: int, is_logged_in: bool) -> str:
    if score <= 29:
        return "ALLOW"
    if score <= 59:
        return "ALLOW_LOG"
    if score <= 79:
        return "ALLOW_LOG" if is_logged_in else "REQUIRE_LOGIN"
    return "ALLOW_LOG" if is_logged_in else "BLOCK"


def _final_score(rule_score: int, ml_result: Any, features: dict[str, Any]) -> int:
    ml_score = max(
        int(float(getattr(ml_result, "fraud_probability", 0) or 0) * 100),
        int(float(getattr(ml_result, "anomaly_score", 0) or 0) * 100),
    )
    if ml_score <= rule_score:
        return int(rule_score)

    # ML is advisory for clean low-risk traffic. It can raise the final score only
    # when the rule/features layer already shows supporting suspicious context.
    if int(rule_score) >= 30 or _has_supporting_ml_signals(features):
        return ml_score
    return int(rule_score)


def _has_supporting_ml_signals(features: dict[str, Any]) -> bool:
    numeric_thresholds = {
        "blocked_attempts": 1,
        "repeated_blocked_attempts": 1,
        "same_fingerprint_multiple_cookies": 1,
        "cookie_missing_after_seen": 1,
        "identity_link_confidence_max": 80,
        "sessions_last_10_min": 4,
        "ips_last_30_min": 4,
        "pdf_attempts_last_10_min": 4,
        "risky_ip_score": 60,
    }
    for key, threshold in numeric_thresholds.items():
        if int(features.get(key, 0) or 0) >= threshold:
            return True
    boolean_flags = (
        "webdriver_detected",
        "headless_suspected",
        "missing_browser_headers",
        "has_vpn_ip",
        "has_proxy_ip",
        "has_datacenter_ip",
        "has_tor_ip",
        "account_created_after_free_limit",
        "api_only_usage_pattern",
    )
    return any(bool(features.get(key)) for key in boolean_flags)


def _severity_for_level(level: str) -> str:
    if level == "CRITICAL":
        return FraudSeverity.CRITICAL.value
    if level == "HIGH":
        return FraudSeverity.HIGH.value
    if level == "MEDIUM":
        return FraudSeverity.MEDIUM.value
    return FraudSeverity.LOW.value


def _last(values: list[Any]) -> Any:
    return values[-1] if values else None
