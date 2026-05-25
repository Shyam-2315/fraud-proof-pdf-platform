from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class ParsedRateLimit:
    raw: str
    limit: int
    window_seconds: int


def parse_rate_limit(value: str) -> ParsedRateLimit:
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
    return floor(now_ts / window_seconds)
