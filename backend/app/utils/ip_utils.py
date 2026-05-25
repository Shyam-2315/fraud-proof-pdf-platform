from ipaddress import ip_address, ip_network
from typing import Any

from fastapi import Request

from app.config import get_settings
from app.utils.security import normalize_ip


def get_client_ip_details(request: Request) -> dict[str, Any]:
    settings = get_settings()
    direct_ip = _direct_client_ip(request)
    trust_proxy_headers = bool(settings.TRUST_PROXY_HEADERS)

    cf_connecting_ip = _clean_header_value(request.headers.get("cf-connecting-ip"))
    x_real_ip = _clean_header_value(request.headers.get("x-real-ip"))
    x_forwarded_for_raw = request.headers.get("x-forwarded-for")
    forwarded_chain = _parse_forwarded_chain(x_forwarded_for_raw)

    resolved_ip = direct_ip
    if trust_proxy_headers:
        resolved_ip = (
            cf_connecting_ip
            or x_real_ip
            or (forwarded_chain[0] if forwarded_chain else None)
            or direct_ip
        )

    proxy_hop_count = max(len(forwarded_chain) - 1, 0)
    private_or_reserved_forwarded = any(_is_private_or_reserved(ip) for ip in forwarded_chain)
    header_mismatch = bool(
        trust_proxy_headers
        and cf_connecting_ip
        and forwarded_chain
        and cf_connecting_ip != forwarded_chain[0]
    )

    return {
        "direct_client_ip": direct_ip,
        "resolved_client_ip": normalize_ip(resolved_ip),
        "cf_connecting_ip": normalize_ip(cf_connecting_ip),
        "x_real_ip": normalize_ip(x_real_ip),
        "x_forwarded_for_raw": x_forwarded_for_raw or "",
        "forwarded_chain": [normalize_ip(ip) for ip in forwarded_chain if normalize_ip(ip)],
        "proxy_hop_count": proxy_hop_count,
        "private_or_reserved_forwarded": private_or_reserved_forwarded,
        "header_mismatch": header_mismatch,
    }


def get_client_ip(request: Request) -> str:
    return get_client_ip_details(request)["resolved_client_ip"]


def get_normalized_client_ip(request: Request) -> str:
    return normalize_ip(get_client_ip(request))


def is_trusted_proxy(client_ip: str, trusted_proxies: list[str]) -> bool:
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


def parse_trusted_proxy_ips(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _direct_client_ip(request: Request) -> str:
    if request.client is None or not request.client.host:
        return "unknown"
    return request.client.host


def _parse_forwarded_chain(value: str | None) -> list[str]:
    if not value:
        return []
    return [cleaned for part in value.split(",") if (cleaned := _clean_header_value(part))]


def _clean_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _is_private_or_reserved(value: str) -> bool:
    try:
        parsed = ip_address(value)
    except ValueError:
        return False
    return bool(
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )
