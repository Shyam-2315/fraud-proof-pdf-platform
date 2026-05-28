"""Backward-compatible database helpers."""

from app.core.database import (
    close_mongo_connection,
    connect_to_mongo,
    get_database,
    ping_mongo,
)

__all__ = [
    "close_mongo_connection",
    "connect_to_mongo",
    "get_database",
    "ping_mongo",
]
