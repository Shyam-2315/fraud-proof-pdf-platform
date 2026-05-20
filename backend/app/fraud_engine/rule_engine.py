from typing import Any

from app.fraud_engine.schemas import RuleReason, RuleResult


class RuleEngine:
    def evaluate(self, features: dict[str, Any]) -> RuleResult:
        reasons: list[RuleReason] = []

        def add(code: str, message: str, points: int) -> None:
            reasons.append(RuleReason(code=code, message=message, points=points))

        if features.get("cookie_missing_after_seen"):
            add("COOKIE_MISSING_AFTER_SEEN", "Cookie missing after previous cookie existed", 15)
        if features.get("same_fingerprint_multiple_cookies"):
            add("SAME_FINGERPRINT_MULTIPLE_COOKIES", "Same fingerprint appeared with multiple cookie IDs", 30)
        if int(features.get("num_local_storage_ids", 0)) >= 1 and int(features.get("num_session_ids", 0)) > 3:
            add("LOCAL_STORAGE_MANY_SESSIONS", "Same local storage ID has many session IDs", 20)
        if int(features.get("sessions_last_10_min", 0)) > 3:
            add("MANY_SESSIONS_10_MIN", "More than 3 sessions in 10 minutes", 20)
        if int(features.get("ips_last_30_min", 0)) > 3:
            add("MANY_IPS_30_MIN", "More than 3 IPs in 30 minutes", 25)
        if features.get("has_tor_ip"):
            add("TOR_IP", "TOR IP detected", 50)
        elif features.get("has_vpn_ip") or features.get("has_proxy_ip") or features.get("has_datacenter_ip"):
            add("VPN_PROXY_DATACENTER_IP", "VPN, proxy, or datacenter IP detected", 30)
        if features.get("webdriver_detected"):
            add("WEBDRIVER_DETECTED", "navigator.webdriver was true", 40)
        if features.get("headless_suspected"):
            add("HEADLESS_SUSPECTED", "Headless or automation indicators detected", 50)
        if float(features.get("time_to_first_generate_seconds", 999999)) < 2:
            add("FAST_FIRST_GENERATE", "PDF generated too quickly after first visit", 25)
        if int(features.get("blocked_attempts", 0)) > 1:
            add("MULTIPLE_BLOCKED_ATTEMPTS", "Multiple blocked attempts", 30)
        if int(features.get("repeated_blocked_attempts", 0)) > 1:
            add("REPEATED_BLOCKED_ATTEMPTS", "Repeated blocked attempts", 30)
        if int(features.get("accounts_same_device", 0)) > 3:
            add("MANY_ACCOUNTS_SAME_DEVICE", "Many accounts from same fingerprint or device", 40)
        if int(features.get("many_visitors_same_ip", 0)) > 3:
            add("MANY_VISITORS_SAME_IP", "Many visitors from same IP", 25)
        if features.get("cleared_cookie_same_fingerprint"):
            add("CLEARED_COOKIE_SAME_FINGERPRINT", "Cleared cookie but same fingerprint matched old visitor", 35)
        if features.get("api_only_usage_pattern"):
            add("API_ONLY_USAGE_PATTERN", "API generation without prior behavior events", 30)
        if int(features.get("same_content_repeated_count", 0)) > 2:
            add("SAME_CONTENT_REPEATED", "Same content generated repeatedly", 20)

        score = min(sum(reason.points for reason in reasons), 100)
        return RuleResult(
            rule_score=score,
            reasons=reasons,
            signals={"same_ip_only": bool(features.get("same_ip_only", False))},
        )
