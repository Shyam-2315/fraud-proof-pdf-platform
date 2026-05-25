from starlette.requests import Request

from app.config import get_settings
from app.utils.request_utils import get_client_ip
from conftest import apply_test_env


def teardown_function() -> None:
    get_settings.cache_clear()


def test_development_forwarded_for_works(monkeypatch) -> None:
    _set_env(monkeypatch, APP_ENV="development", TRUST_PROXY_HEADERS="false")
    request = _request(
        client_host="127.0.0.1",
        headers={"X-Forwarded-For": "198.51.100.10, 10.0.0.2"},
    )

    assert get_client_ip(request) == "198.51.100.10"


def test_production_without_trust_ignores_forwarded_for(monkeypatch) -> None:
    _set_env(monkeypatch, APP_ENV="production", TRUST_PROXY_HEADERS="false")
    request = _request(
        client_host="172.25.0.5",
        headers={"X-Forwarded-For": "198.51.100.20"},
    )

    assert get_client_ip(request) == "172.25.0.5"


def test_production_with_trusted_proxy_uses_forwarded_for(monkeypatch) -> None:
    _set_env(
        monkeypatch,
        APP_ENV="production",
        TRUST_PROXY_HEADERS="true",
        TRUSTED_PROXY_IPS="172.25.0.0/16",
    )
    request = _request(
        client_host="172.25.0.5",
        headers={"X-Forwarded-For": "198.51.100.30"},
    )

    assert get_client_ip(request) == "198.51.100.30"


def test_fallback_works_when_request_client_is_missing(monkeypatch) -> None:
    _set_env(monkeypatch, APP_ENV="production", TRUST_PROXY_HEADERS="false")
    request = _request(client_host=None, headers={})

    assert get_client_ip(request) == "unknown"


def _set_env(monkeypatch, **values: str) -> None:
    apply_test_env(monkeypatch, **values)


def _request(client_host: str | None, headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": (client_host, 12345) if client_host else None,
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)
