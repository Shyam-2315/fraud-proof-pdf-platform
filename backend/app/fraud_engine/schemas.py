from dataclasses import dataclass, field
from typing import Any, Literal


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Decision = Literal["ALLOW", "ALLOW_LOG", "REQUIRE_LOGIN", "BLOCK"]


FEATURE_COLUMNS = [
    "num_cookie_ids",
    "num_local_storage_ids",
    "num_session_ids",
    "num_fingerprint_hashes",
    "num_device_profile_hashes",
    "num_canvas_hashes",
    "num_webgl_hashes",
    "num_ip_addresses",
    "num_user_agents",
    "ip_change_count",
    "sessions_last_10_min",
    "ips_last_30_min",
    "pdf_attempts_last_10_min",
    "blocked_attempts",
    "repeated_blocked_attempts",
    "time_to_first_generate_seconds",
    "avg_time_between_generations",
    "same_content_repeated_count",
    "api_only_usage_pattern",
    "page_views_before_generate",
    "generate_clicks_before_success",
    "has_vpn_ip",
    "has_proxy_ip",
    "has_datacenter_ip",
    "has_tor_ip",
    "risky_ip_score",
    "webdriver_detected",
    "plugins_count",
    "headless_suspected",
    "missing_browser_headers",
    "cookie_missing_after_seen",
    "same_fingerprint_multiple_cookies",
    "accounts_same_device",
    "accounts_same_ip",
    "account_created_after_free_limit",
    "identity_link_confidence_max",
    "many_visitors_same_ip",
    "cleared_cookie_same_fingerprint",
    "same_ip_only",
]


@dataclass
class RuleReason:
    code: str
    message: str
    points: int

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "points": self.points}


@dataclass
class RuleResult:
    rule_score: int
    reasons: list[RuleReason] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)

    def reason_dicts(self) -> list[dict[str, Any]]:
        return [reason.as_dict() for reason in self.reasons]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_score": self.rule_score,
            "reasons": self.reason_dicts(),
        }

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]


@dataclass
class MLResult:
    fraud_probability: float = 0.0
    anomaly_score: float = 0.0
    model_version: str = "none"


@dataclass
class FraudDecisionResult:
    fraud_probability: float
    anomaly_score: float
    rule_score: int
    final_risk_score: int
    risk_level: RiskLevel
    decision: Decision
    reasons: list[dict[str, Any]]
    model_version: str = "none"
    decision_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "fraud_probability": self.fraud_probability,
            "anomaly_score": self.anomaly_score,
            "rule_score": self.rule_score,
            "final_risk_score": self.final_risk_score,
            "risk_score": self.final_risk_score,
            "risk_level": self.risk_level,
            "decision": self.decision,
            "reasons": self.reasons,
            "model_version": self.model_version,
            "decision_id": self.decision_id,
        }

    def __getitem__(self, key: str) -> Any:
        return self.as_dict()[key]


def risk_level_for_score(score: int) -> RiskLevel:
    if score <= 29:
        return "LOW"
    if score <= 59:
        return "MEDIUM"
    if score <= 79:
        return "HIGH"
    return "CRITICAL"
