from enum import StrEnum


VISITOR_COLLECTION = "visitors"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
