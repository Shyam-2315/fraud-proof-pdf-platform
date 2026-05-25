from ipaddress import ip_address, ip_network

from fastapi import Request

from app.config import get_settings
from app.utils.security import normalize_ip


def get_client_ip(request: Request) -> str:
    settings = get_settings()
    direct_ip = _direct_client_ip(request)

    if settings.APP_ENV.lower() == "development":
        return _first_forwarded_ip(request) or direct_ip

    if (
        settings.APP_ENV.lower() == "production"
        and settings.TRUST_PROXY_HEADERS
        and _is_trusted_proxy(direct_ip, _parse_trusted_proxy_ips(settings.TRUSTED_PROXY_IPS))
    ):
        return _first_forwarded_ip(request) or direct_ip

    if settings.APP_ENV.lower() != "production" and settings.TRUST_PROXY_HEADERS:
        return _first_forwarded_ip(request) or direct_ip

    return direct_ip


def get_normalized_client_ip(request: Request) -> str:
    return normalize_ip(get_client_ip(request))


def _direct_client_ip(request: Request) -> str:
    if request.client is None or not request.client.host:
        return "unknown"
    return request.client.host


def _first_forwarded_ip(request: Request) -> str | None:
    cloudflare_ip = _clean_header_value(request.headers.get("cf-connecting-ip"))
    if cloudflare_ip:
        return cloudflare_ip

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = _clean_header_value(forwarded_for.split(",", 1)[0])
        if first_ip:
            return first_ip

    return _clean_header_value(request.headers.get("x-real-ip"))


def _clean_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _is_trusted_proxy(client_ip: str, trusted_proxies: list[str]) -> bool:
    if not trusted_proxies:
        return False
    if "*" in trusted_proxies:
        return True
    try:
        parsed_ip = ip_address(client_ip)
    except ValueError:
        return False

    for trusted_proxy in trusted_proxies:
        try:
            if "/" in trusted_proxy:
                if parsed_ip in ip_network(trusted_proxy, strict=False):
                    return True
            elif parsed_ip == ip_address(trusted_proxy):
                return True
        except ValueError:
            continue
    return False


def _parse_trusted_proxy_ips(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
