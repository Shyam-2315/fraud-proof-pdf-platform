from datetime import UTC, datetime
from typing import TypeVar
from uuid import uuid4

T = TypeVar("T")


def generate_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_ip(ip: str) -> str:
    return ip.strip() if ip else ""


def safe_append_unique(
    existing_list: list[T] | None,
    value: T | None,
    max_items: int = 20,
) -> list[T]:
    values = list(existing_list or [])
    if value is None:
        return values[-max_items:]

    if isinstance(value, str) and not value.strip():
        return values[-max_items:]

    if value not in values:
        values.append(value)

    return values[-max_items:]
