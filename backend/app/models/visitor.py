from enum import StrEnum


VISITOR_COLLECTION = "visitors"


class RiskLevel(StrEnum):
    """
    Model describing the risk level domain object.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
