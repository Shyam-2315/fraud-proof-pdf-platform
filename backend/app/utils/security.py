from datetime import UTC, datetime
from typing import TypeVar
from uuid import uuid4

T = TypeVar("T")


def generate_uuid() -> str:
    """
    Generate a random UUID string for persistent identifiers.

    Returns:
        Newly generated UUID string.
    """
    return str(uuid4())


def utc_now() -> datetime:
    """
    Return the current timezone-aware UTC timestamp.

    Returns:
        Current UTC datetime with timezone information.
    """
    return datetime.now(UTC)


def normalize_ip(ip: str) -> str:
    """
    Normalize an IP string by trimming surrounding whitespace.

    Args:
        ip: Raw IP address string or empty value.

    Returns:
        Trimmed IP address string, or an empty string when no value is present.
    """
    return ip.strip() if ip else ""


def safe_append_unique(
    existing_list: list[T] | None,
    value: T | None,
    max_items: int = 20,
) -> list[T]:
    """
    Append a value to a list only when it is non-empty and not already present.

    Args:
        existing_list: Existing ordered values to preserve.
        value: Candidate value to append.
        max_items: Maximum number of items to keep from the tail of the list.

    Returns:
        Deduplicated list trimmed to the configured maximum size.
    """
    values = list(existing_list or [])
    if value is None:
        return values[-max_items:]

    if isinstance(value, str) and not value.strip():
        return values[-max_items:]

    if value not in values:
        values.append(value)

    return values[-max_items:]
