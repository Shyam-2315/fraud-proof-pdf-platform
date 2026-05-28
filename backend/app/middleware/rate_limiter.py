from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class ParsedRateLimit:
    """Parsed representation of a configured rate-limit string."""

    raw: str
    limit: int
    window_seconds: int


def parse_rate_limit(value: str) -> ParsedRateLimit:
    """
    Parse a rate-limit string such as ``"30/minute"`` into structured values.

    Args:
        value: Raw rate-limit string from configuration.

    Returns:
        Parsed limit object containing the numeric limit and window size.

    Raises:
        ValueError: If the rate-limit unit is not supported.
    """
    raw = value.strip().lower()
    limit_text, _, unit_text = raw.partition("/")
    limit = int(limit_text)
    unit = unit_text.strip()
    if unit == "minute":
        window_seconds = 60
    elif unit == "hour":
        window_seconds = 3600
    else:
        raise ValueError(f"Unsupported rate limit unit: {value}")
    return ParsedRateLimit(raw=value, limit=limit, window_seconds=window_seconds)


def sliding_window_bucket(now_ts: float, window_seconds: int) -> int:
    """
    Compute the current sliding-window bucket for a timestamp.

    Args:
        now_ts: Current timestamp expressed in seconds since epoch.
        window_seconds: Window size in seconds.

    Returns:
        Integer bucket identifier for the provided timestamp.
    """
    return floor(now_ts / window_seconds)
