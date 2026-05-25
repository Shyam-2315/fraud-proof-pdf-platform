#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path


DEFAULT_VALUES = {
    "JWT_SECRET_KEY": {
        "change-me-super-secret",
        "change-me-in-production",
        "replace-with-strong-secret",
    },
    "ADMIN_API_KEY": {
        "change-me-admin-key",
        "replace-with-strong-admin-key",
    },
    "DEFAULT_ADMIN_PASSWORD": {
        "AdminPassword123",
        "replace-with-strong-admin-password",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PDFCraft production env safety.")
    parser.add_argument("--env", default="backend/.env.production", help="Backend env file")
    parser.add_argument(
        "--compose",
        default="docker-compose.prod.yml",
        help="Production compose file",
    )
    args = parser.parse_args()

    env_path = Path(args.env)
    compose_path = Path(args.compose)
    env = _read_env(env_path)
    compose_text = compose_path.read_text() if compose_path.exists() else ""

    checks: list[tuple[str, bool, str]] = [
        ("env file exists", env_path.exists(), str(env_path)),
        ("compose file exists", compose_path.exists(), str(compose_path)),
        ("APP_ENV=production", env.get("APP_ENV") == "production", env.get("APP_ENV", "")),
        (
            "JWT_SECRET_KEY changed",
            _strong_value(env.get("JWT_SECRET_KEY"), "JWT_SECRET_KEY", 24),
            "replace placeholder JWT secret",
        ),
        (
            "ADMIN_API_KEY changed",
            _strong_value(env.get("ADMIN_API_KEY"), "ADMIN_API_KEY", 24),
            "replace placeholder admin API key",
        ),
        (
            "DEFAULT_ADMIN_PASSWORD changed if seeding enabled",
            env.get("ENABLE_DEFAULT_ADMIN_SEED", "").lower() != "true"
            or _strong_value(env.get("DEFAULT_ADMIN_PASSWORD"), "DEFAULT_ADMIN_PASSWORD", 16),
            "disable seeding or replace DEFAULT_ADMIN_PASSWORD",
        ),
        (
            "ENABLE_DEFAULT_ADMIN_SEED=false recommended",
            env.get("ENABLE_DEFAULT_ADMIN_SEED", "").lower() == "false",
            env.get("ENABLE_DEFAULT_ADMIN_SEED", ""),
        ),
        (
            "SECURE_COOKIES=true",
            env.get("SECURE_COOKIES", "").lower() == "true",
            env.get("SECURE_COOKIES", ""),
        ),
        (
            "TRUST_PROXY_HEADERS=true only with reverse proxy configured",
            env.get("TRUST_PROXY_HEADERS", "").lower() != "true" or "reverse-proxy:" in compose_text,
            "set TRUST_PROXY_HEADERS=true only behind the configured reverse proxy",
        ),
        (
            "CORS_ORIGINS excludes localhost",
            _no_localhost(env.get("CORS_ORIGINS", "")),
            env.get("CORS_ORIGINS", ""),
        ),
        (
            "FRONTEND_URL uses HTTPS",
            env.get("FRONTEND_URL", "").startswith("https://"),
            env.get("FRONTEND_URL", ""),
        ),
        (
            "ADMIN_FRONTEND_URL uses HTTPS",
            env.get("ADMIN_FRONTEND_URL", "").startswith("https://"),
            env.get("ADMIN_FRONTEND_URL", ""),
        ),
        (
            "BACKEND_PUBLIC_URL uses HTTPS",
            env.get("BACKEND_PUBLIC_URL", "").startswith("https://"),
            env.get("BACKEND_PUBLIC_URL", ""),
        ),
        (
            "ENABLE_API_DOCS=false recommended",
            env.get("ENABLE_API_DOCS", "").lower() == "false",
            env.get("ENABLE_API_DOCS", ""),
        ),
    ]

    if compose_text:
        checks.extend(
            [
                (
                    "reverse-proxy service present",
                    "reverse-proxy:" in compose_text,
                    "docker-compose.prod.yml",
                ),
                (
                    "MongoDB has no public ports",
                    not _service_has_ports(compose_text, "mongodb"),
                    "mongodb",
                ),
                (
                    "Redis has no public ports",
                    not _service_has_ports(compose_text, "redis"),
                    "redis",
                ),
                (
                    "backend has no public ports",
                    not _service_has_ports(compose_text, "backend"),
                    "backend",
                ),
                (
                    "frontend has no public ports",
                    not _service_has_ports(compose_text, "frontend"),
                    "frontend",
                ),
                (
                    "admin-frontend has no public ports",
                    not _service_has_ports(compose_text, "admin-frontend"),
                    "admin-frontend",
                ),
            ]
        )

    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        suffix = f" ({detail})" if detail else ""
        print(f"{status}: {name}{suffix}")
        all_passed = all_passed and passed

    return 0 if all_passed else 1


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _strong_value(value: str | None, key: str, min_length: int) -> bool:
    if value is None:
        return False
    return value not in DEFAULT_VALUES[key] and len(value) >= min_length


def _no_localhost(value: str) -> bool:
    return "localhost" not in value and "127.0.0.1" not in value


def _service_has_ports(compose_text: str, service: str) -> bool:
    pattern = re.compile(
        rf"^  {re.escape(service)}:\n(?P<body>(?:    .*\n|      .*\n|        .*\n)*)",
        re.MULTILINE,
    )
    match = pattern.search(compose_text)
    if not match:
        return False
    return bool(re.search(r"^    ports:\s*$", match.group("body"), re.MULTILINE))


if __name__ == "__main__":
    sys.exit(main())
