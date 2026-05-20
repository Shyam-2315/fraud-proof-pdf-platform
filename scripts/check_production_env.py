#!/usr/bin/env python3
import argparse
from pathlib import Path
import re
import sys


DEFAULT_VALUES = {
    "JWT_SECRET_KEY": {
        "change-me-super-secret",
        "change-me-in-production",
    },
    "ADMIN_API_KEY": {
        "change-me-admin-key",
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
    checks: list[tuple[str, bool, str]] = []

    env = _read_env(env_path)
    checks.append(("env file exists", env_path.exists(), str(env_path)))
    checks.append(("APP_ENV=production", env.get("APP_ENV") == "production", env.get("APP_ENV", "")))
    checks.append(
        (
            "JWT_SECRET_KEY changed",
            _strong_value(env.get("JWT_SECRET_KEY"), "JWT_SECRET_KEY", 24),
            "set strong JWT_SECRET_KEY",
        )
    )
    checks.append(
        (
            "ADMIN_API_KEY changed",
            _strong_value(env.get("ADMIN_API_KEY"), "ADMIN_API_KEY", 24),
            "set strong ADMIN_API_KEY",
        )
    )
    checks.append(
        (
            "CORS_ORIGINS not localhost",
            "localhost" not in env.get("CORS_ORIGINS", "") and "127.0.0.1" not in env.get("CORS_ORIGINS", ""),
            env.get("CORS_ORIGINS", ""),
        )
    )
    checks.append(("FRONTEND_URL uses HTTPS", env.get("FRONTEND_URL", "").startswith("https://"), env.get("FRONTEND_URL", "")))
    checks.append(("BACKEND_PUBLIC_URL uses HTTPS", env.get("BACKEND_PUBLIC_URL", "").startswith("https://"), env.get("BACKEND_PUBLIC_URL", "")))
    checks.append(("SECURE_COOKIES=true", env.get("SECURE_COOKIES", "").lower() == "true", env.get("SECURE_COOKIES", "")))
    checks.append(
        (
            "default admin seed disabled or password changed",
            env.get("ENABLE_DEFAULT_ADMIN_SEED", "").lower() == "false"
            or env.get("DEFAULT_ADMIN_PASSWORD") not in {"", None, "AdminPassword123", "replace-with-strong-admin-password"},
            "set ENABLE_DEFAULT_ADMIN_SEED=false or change DEFAULT_ADMIN_PASSWORD",
        )
    )
    checks.append(("prod compose exists", compose_path.exists(), str(compose_path)))
    if compose_path.exists():
        compose_text = compose_path.read_text()
        checks.append(("MongoDB has no public ports", not _service_has_ports(compose_text, "mongodb"), "mongodb"))
        checks.append(("Redis has no public ports", not _service_has_ports(compose_text, "redis"), "redis"))

    all_passed = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}" + (f" ({detail})" if detail else ""))
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


def _service_has_ports(compose_text: str, service: str) -> bool:
    pattern = re.compile(rf"^  {re.escape(service)}:\n(?P<body>(?:    .*\n|      .*\n|        .*\n)*)", re.MULTILINE)
    match = pattern.search(compose_text)
    if not match:
        return False
    return bool(re.search(r"^    ports:\s*$", match.group("body"), re.MULTILINE))


if __name__ == "__main__":
    sys.exit(main())
