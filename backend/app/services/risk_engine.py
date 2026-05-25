from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskDecision:
    decision: str
    reasons: list[dict[str, Any]]
    score: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reasons": self.reasons,
            "risk_score": self.score,
        }


class RiskEngine:
    def decide(self, signals: dict[str, Any]) -> RiskDecision:
        reasons: list[dict[str, Any]] = []
        score = 0

        shared_usage = int(signals.get("shared_usage_count", 0))
        shared_limit = int(signals.get("anon_shared_limit", 2))
        unique_visitors = int(signals.get("unique_visitors_from_ip", 0))
        proxy_chain_hop_count = int(signals.get("proxy_chain_hop_count", 0))
        vpn_proxy_score = int(signals.get("vpn_proxy_score", 0))
        ip_change_count = int(signals.get("ip_change_count", 0))
        fingerprint_reuse_count = int(signals.get("fingerprint_reuse_count", 0))
        session_count = int(signals.get("session_count", 0))
        user_agent_count = int(signals.get("user_agent_count", 0))
        webdriver_detected = bool(signals.get("webdriver_detected", False))
        rapid_generate_attempts = bool(signals.get("rapid_generate_attempts", False))
        no_behavior_before_generate = bool(signals.get("no_behavior_before_generate", False))
        is_datacenter = bool(signals.get("is_datacenter", False))

        if shared_usage >= shared_limit:
            reasons.append({"code": "SHARED_LIMIT", "score": 100})
            return RiskDecision("REQUIRE_LOGIN", reasons, 100)

        if webdriver_detected:
            reasons.append({"code": "WEBDRIVER", "score": 100})
            return RiskDecision("BLOCK", reasons, 100)

        if unique_visitors > 10:
            reasons.append({"code": "MANY_VISITORS_SAME_IP", "score": 85})
            return RiskDecision("REQUIRE_LOGIN", reasons, 85)

        if rapid_generate_attempts and no_behavior_before_generate:
            reasons.append({"code": "RAPID_NO_BEHAVIOR", "score": 75})
            return RiskDecision("REQUIRE_LOGIN", reasons, 75)

        if vpn_proxy_score > 80 and unique_visitors > 3:
            reasons.append({"code": "HIGH_RISK_IP_CLUSTER", "score": 80})
            return RiskDecision("REQUIRE_LOGIN", reasons, 80)

        if ip_change_count > 5:
            reasons.append({"code": "DYNAMIC_IP_CHURN", "score": 80})
            return RiskDecision("REQUIRE_LOGIN", reasons, 80)

        if proxy_chain_hop_count > 3:
            score = max(score, 45)
            reasons.append({"code": "PROXY_CHAIN", "score": 45})
        if is_datacenter or vpn_proxy_score > 0:
            score = max(score, vpn_proxy_score)
            reasons.append({"code": "RISKY_NETWORK", "score": vpn_proxy_score})
        if fingerprint_reuse_count > 3:
            score = max(score, 35)
            reasons.append({"code": "FINGERPRINT_REUSE", "score": 35})
        if session_count > 5:
            score = max(score, 25)
            reasons.append({"code": "MANY_SESSIONS", "score": 25})
        if user_agent_count > 3:
            score = max(score, 20)
            reasons.append({"code": "MANY_USER_AGENTS", "score": 20})

        return RiskDecision("ALLOW", reasons, score)
