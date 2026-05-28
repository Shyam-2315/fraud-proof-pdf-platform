from enum import StrEnum


RISK_SCORE_SNAPSHOTS_COLLECTION = "risk_score_snapshots"
IP_INTELLIGENCE_COLLECTION = "ip_intelligence"


class RiskLevel(StrEnum):
    """
    Model describing the risk level domain object.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
