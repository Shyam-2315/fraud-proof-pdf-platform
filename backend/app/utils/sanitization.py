import json
import re
from collections.abc import Mapping
from html import unescape
from typing import Any

_SCRIPT_TAG_RE = re.compile(r"<\s*/?\s*script\b", re.IGNORECASE)
_EVENT_HANDLER_RE = re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE)
_JS_URL_RE = re.compile(r"javascript\s*:", re.IGNORECASE)
_SRCDOC_RE = re.compile(r"\bsrcdoc\b", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[^\S\n]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_MAX_LOG_VALUE_LENGTH = 512
_REDACTED_VALUE = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "api_key",
    "secret",
)


def strip_html_tags(text: str) -> str:
    """Remove HTML tags and decode common entities from a text value."""
    if not isinstance(text, str):
        return ""
    without_tags = _HTML_TAG_RE.sub("", text)
    return unescape(without_tags)


def sanitize_plain_text(text: str, max_length: int | None = None) -> str:
    """Normalize plain text while stripping HTML tags and unsafe control bytes."""
    if not isinstance(text, str):
        raise TypeError("Expected a string value.")

    normalized = strip_html_tags(text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = _CONTROL_CHAR_RE.sub("", normalized)
    normalized = "\n".join(_WHITESPACE_RE.sub(" ", line).strip() for line in normalized.split("\n"))
    normalized = _MULTI_NEWLINE_RE.sub("\n\n", normalized).strip()
    if max_length is not None:
        normalized = normalized[:max_length].rstrip()
    return normalized


def contains_xss_payload(text: str) -> bool:
    """Detect obvious XSS payload markers in user-controlled text."""
    if not isinstance(text, str):
        return False
    lowered = unescape(text)
    return any(
        pattern.search(lowered)
        for pattern in (_SCRIPT_TAG_RE, _EVENT_HANDLER_RE, _JS_URL_RE, _SRCDOC_RE)
    )


def sanitize_log_value(value: Any) -> str:
    """Convert untrusted values into a safe, bounded plain-text representation."""
    rendered = _stringify_value(value)
    sanitized = sanitize_plain_text(rendered, max_length=_MAX_LOG_VALUE_LENGTH)
    return sanitized or ""


def sanitize_mapping(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Recursively sanitize mapping values for safe storage and serialization."""
    if data is None:
        return {}

    return {
        sanitize_log_value(key): (
            _REDACTED_VALUE if _is_sensitive_key(key) else sanitize_value(item)
        )
        for key, item in data.items()
    }


def sanitize_value(value: Any) -> Any:
    """Recursively sanitize user-controlled values while preserving basic shapes."""
    if isinstance(value, str):
        return sanitize_log_value(value)
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_value(item) for item in value]
    if isinstance(value, set):
        return [sanitize_value(item) for item in sorted(value, key=_stringify_value)]
    return value


def _is_sensitive_key(key: Any) -> bool:
    normalized = sanitize_log_value(key).lower().replace("-", "_").replace(" ", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return json.dumps(value, default=str, ensure_ascii=True, sort_keys=True)
        except TypeError:
            return str(value)
    return str(value)
