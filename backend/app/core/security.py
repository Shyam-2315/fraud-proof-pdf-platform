"""Backward-compatible security helpers exposed from core."""

from app.utils.security import generate_uuid, utc_now

__all__ = ["generate_uuid", "utc_now"]
