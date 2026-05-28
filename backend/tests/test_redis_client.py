"""Tests for shared Redis client lifecycle handling."""

import asyncio
from types import SimpleNamespace

import pytest

import app.redis_client as redis_client


class _FakeRedis:
    """Minimal async Redis test double."""

    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self.ping_error = ping_error
        self.ping_calls = 0
        self.closed = False

    async def ping(self) -> bool:
        self.ping_calls += 1
        if self.ping_error is not None:
            raise self.ping_error
        return True

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _reset_redis_state() -> None:
    """Clear cached Redis client state between tests."""
    redis_client._redis = None
    redis_client._redis_error = None


def test_connect_to_redis_initializes_shared_client(monkeypatch) -> None:
    """Successful startup should cache one Redis client for later health checks."""
    fake_client = _FakeRedis()
    monkeypatch.setattr(
        redis_client,
        "get_settings",
        lambda: SimpleNamespace(REDIS_URL="rediss://default:secret@example.upstash.io:6379", APP_ENV="production"),
    )
    monkeypatch.setattr(redis_client.redis, "from_url", lambda *args, **kwargs: fake_client)

    asyncio.run(redis_client.connect_to_redis())

    assert redis_client.get_redis() is fake_client
    assert asyncio.run(redis_client.ping_redis()) is True
    assert fake_client.ping_calls >= 2


def test_connect_to_redis_retains_connection_error_for_health(monkeypatch) -> None:
    """Failed initialization should preserve the actual connection error text."""
    fake_client = _FakeRedis(ping_error=RuntimeError("upstash timeout"))
    monkeypatch.setattr(
        redis_client,
        "get_settings",
        lambda: SimpleNamespace(REDIS_URL="rediss://default:secret@example.upstash.io:6379", APP_ENV="production"),
    )
    monkeypatch.setattr(redis_client.redis, "from_url", lambda *args, **kwargs: fake_client)

    asyncio.run(redis_client.connect_to_redis())

    with pytest.raises(RuntimeError, match="Redis connection failed: upstash timeout"):
        asyncio.run(redis_client.ping_redis())
    assert fake_client.closed is True


def test_connect_to_redis_allows_missing_local_configuration(monkeypatch) -> None:
    """Local startup should continue when Redis is intentionally not configured."""
    monkeypatch.setattr(
        redis_client,
        "get_settings",
        lambda: SimpleNamespace(REDIS_URL="", APP_ENV="local"),
    )

    asyncio.run(redis_client.connect_to_redis())

    with pytest.raises(RuntimeError, match="Redis URL is not configured"):
        redis_client.get_redis()
