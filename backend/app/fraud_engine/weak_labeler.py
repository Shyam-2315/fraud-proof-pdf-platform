from typing import Any


def weak_label_from_rule_score(
    rule_score: int,
    features: dict[str, Any],
    normal_flow: bool = False,
) -> dict[str, Any]:
    """
    Derive a weak training label from rule-engine output and supporting features.

    Args:
        rule_score: Fraud rule score computed for the action.
        features: Fraud feature snapshot associated with the action.
        normal_flow: Whether the action occurred in a customer flow already considered normal.

    Returns:
        Weak-label payload containing the label, source, and confidence used for
        fraud-training events.
    """
    same_ip_only = (
        int(features.get("num_ip_addresses", 0)) > 0
        and int(features.get("num_cookie_ids", 0)) <= 1
        and int(features.get("num_fingerprint_hashes", 0)) <= 1
        and int(features.get("num_device_profile_hashes", 0)) <= 1
        and int(features.get("identity_link_confidence_max", 0)) < 50
    )
    if same_ip_only and rule_score < 60:
        return {
            "outcome_label": None,
            "label_source": "UNKNOWN",
            "label_confidence": 0.0,
        }
    if rule_score >= 80:
        return {
            "outcome_label": 1,
            "label_source": "RULE_ENGINE",
            "label_confidence": 0.90,
        }
    if rule_score >= 60:
        return {
            "outcome_label": 1,
            "label_source": "RULE_ENGINE",
            "label_confidence": 0.70,
        }
    if rule_score <= 20 and normal_flow:
        return {
            "outcome_label": 0,
            "label_source": "RULE_ENGINE",
            "label_confidence": 0.75,
        }
    return {
        "outcome_label": None,
        "label_source": "UNKNOWN",
        "label_confidence": 0.0,
    }
