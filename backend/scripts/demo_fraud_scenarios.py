import argparse
import json
from uuid import uuid4

import httpx


BASE_URL = "http://localhost:8025"
ADMIN_API_KEY = "change-me-admin-key"


def scenario_headers(prefix: str, ip_address: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": f"PDFCraftDemo/{prefix}",
        "X-Visitor-Id": f"demo-rate-{prefix}",
    }
    if ip_address:
        headers["X-Forwarded-For"] = ip_address
    if extra:
        headers.update(extra)
    return headers


def print_json(label: str, value: object) -> None:
    print(f"{label}:")
    print(json.dumps(value, indent=2, default=str))


def print_response(label: str, response: httpx.Response) -> None:
    try:
        body: object = response.json()
    except ValueError:
        body = response.text
    print(f"{label}: HTTP {response.status_code}")
    print(json.dumps(body, indent=2, default=str) if not isinstance(body, str) else body)


def identify(client: httpx.Client, prefix: str, **overrides: str) -> dict:
    payload = {
        "local_storage_id": overrides.get("local_storage_id", f"{prefix}-local"),
        "session_id": overrides.get("session_id", f"{prefix}-session"),
        "fingerprint_hash": overrides.get("fingerprint_hash", f"{prefix}-fingerprint"),
        "device_profile_hash": overrides.get("device_profile_hash", f"{prefix}-device"),
        "canvas_hash": overrides.get("canvas_hash", f"{prefix}-canvas"),
        "webgl_hash": overrides.get("webgl_hash", f"{prefix}-webgl"),
        "audio_hash": overrides.get("audio_hash", f"{prefix}-audio"),
        "device_info": {
            "screen": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux x86_64",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "touch_support": 0,
            "plugins_count": 5,
        },
        "automation_signals": {
            "webdriver": overrides.get("webdriver", "false") == "true",
            "plugins_count": int(overrides.get("plugins_count", "5")),
            "cookies_enabled": True,
            "local_storage_available": True,
            "session_storage_available": True,
        },
    }
    response = client.post("/api/visitor/identify", json=payload)
    response.raise_for_status()
    return response.json()


def generate(client: httpx.Client, title: str = "Demo PDF") -> httpx.Response:
    return client.post(
        "/api/pdf/generate",
        json={"title": title, "content": "Demo scenario content."},
    )


def banner(title: str, proof: str) -> None:
    print(f"\n=== {title} ===")
    print(f"Proves: {proof}")


def normal_visitor() -> None:
    banner("Normal visitor", "Two anonymous PDFs are allowed and the third requires login.")
    prefix = f"demo-normal-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(prefix, "198.51.100.30")) as client:
        print_json("Identify", identify(client, prefix))
        print_response("PDF 1", generate(client, "Normal 1"))
        print_response("PDF 2", generate(client, "Normal 2"))
        print_response("PDF 3", generate(client, "Normal 3"))


def same_fingerprint_new_cookie() -> None:
    banner("Same fingerprint with new cookie", "Clearing cookies does not reset usage when strong identity signals match.")
    prefix = f"demo-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(f"{prefix}-a", "198.51.100.31")) as first:
        first_identify = identify(first, prefix)
        print_json("First cookie identify", first_identify)
        print_response("PDF 1", generate(first, "Cookie A 1"))
        print_response("PDF 2", generate(first, "Cookie A 2"))
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(f"{prefix}-b", "198.51.100.32")) as second:
        second_identify = identify(second, prefix, local_storage_id=f"{prefix}-local-2", session_id=f"{prefix}-session-2")
        print_json("New cookie identify", second_identify)
        print("Reused visitor:", second_identify.get("visitor_id") == first_identify.get("visitor_id"))
        print_response("PDF 3 after cookie clear", generate(second, "Cookie B 3"))


def multiple_sessions() -> None:
    banner("Multiple sessions", "Session churn links back to the same visitor and raises internal risk.")
    prefix = f"demo-sessions-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(prefix, "198.51.100.33")) as client:
        for index in range(5):
            print_json(f"Session {index + 1}", identify(client, prefix, session_id=f"{prefix}-session-{index}"))


def vpn_ip() -> None:
    banner("Risky IP from local risk list", "Local IP intelligence flags VPN/proxy/datacenter IPs without external APIs.")
    prefix = f"demo-vpn-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(prefix, "203.0.113.66")) as client:
        print_json("Identify", identify(client, prefix))
        print_response("Generate", generate(client, "Risky IP PDF"))


def rapid_generation() -> None:
    banner("Rapid generation attempts", "Fast repeated generation attempts create admin-visible signals.")
    prefix = f"demo-rapid-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(prefix, "198.51.100.34")) as client:
        identify(client, prefix)
        for index in range(5):
            print_response(f"Rapid attempt {index + 1}", generate(client, f"Rapid {index + 1}"))


def automation() -> None:
    banner("Automation signal", "webdriver/headless indicators increase internal risk.")
    prefix = f"demo-auto-{uuid4()}"
    headers = scenario_headers(prefix, "198.51.100.35", {"User-Agent": "Mozilla/5.0 HeadlessChrome"})
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=headers) as client:
        print_json("Identify with webdriver=true", identify(client, prefix, webdriver="true", plugins_count="0"))
        print_response("Generate", generate(client, "Automation PDF"))


def changed_ip_same_visitor() -> None:
    banner("Same visitor with changed IP", "Changing IP does not reset usage when fingerprint/localStorage match.")
    prefix = f"demo-ip-change-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(f"{prefix}-a", "198.51.100.40")) as first:
        first_identify = identify(first, prefix)
        print_json("First IP identify", first_identify)
        print_response("PDF 1", generate(first, "Before IP change 1"))
        print_response("PDF 2", generate(first, "Before IP change 2"))
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(f"{prefix}-b", "198.51.100.41")) as second:
        second_identify = identify(second, prefix, session_id=f"{prefix}-session-2")
        print_json("Changed IP identify", second_identify)
        print("Reused visitor:", second_identify.get("visitor_id") == first_identify.get("visitor_id"))
        print_response("PDF 3 after IP change", generate(second, "After IP change 3"))


def login_after_anonymous_block() -> None:
    banner("Logged-in user after anonymous block", "Authenticated monthly limits win over anonymous blocked state.")
    prefix = f"demo-login-{uuid4()}"
    email = f"{prefix}@example.com"
    with httpx.Client(base_url=BASE_URL, timeout=10, headers=scenario_headers(prefix, "198.51.100.42")) as client:
        identify(client, prefix)
        print_response("Anon 1", generate(client, "Anon 1"))
        print_response("Anon 2", generate(client, "Anon 2"))
        print_response("Anon 3", generate(client, "Anon 3"))
        registered = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "full_name": "Demo User",
                "password": "StrongPassword123",
            },
        )
        print_response("Register", registered)
        token = registered.json().get("access_token")
        authed = client.post(
            "/api/pdf/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Logged in after block", "content": "Authenticated demo"},
        )
        print_response("Authenticated PDF", authed)


def print_admin_commands() -> None:
    print("\nAdmin follow-up commands:")
    print(f"curl -i {BASE_URL}/api/admin/ml/models -H 'X-Admin-API-Key: {ADMIN_API_KEY}'")
    print(f"curl -i {BASE_URL}/api/admin/fraud/decisions -H 'X-Admin-API-Key: {ADMIN_API_KEY}'")
    print(f"curl -i {BASE_URL}/api/admin/fraud/events -H 'X-Admin-API-Key: {ADMIN_API_KEY}'")


SCENARIOS = {
    "NORMAL_VISITOR": normal_visitor,
    "CLEAR_COOKIE_SAME_FINGERPRINT": same_fingerprint_new_cookie,
    "CHANGED_IP_SAME_VISITOR": changed_ip_same_visitor,
    "MULTIPLE_SESSIONS": multiple_sessions,
    "VPN_IP": vpn_ip,
    "RAPID_GENERATION": rapid_generation,
    "AUTOMATION": automation,
    "LOGGED_IN_AFTER_ANONYMOUS_BLOCK": login_after_anonymous_block,
}


def main() -> None:
    global BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS))
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")
    if args.scenario:
        SCENARIOS[args.scenario]()
        print_admin_commands()
        return
    for scenario in SCENARIOS.values():
        try:
            scenario()
        except Exception as exc:  # noqa: BLE001
            print(f"Scenario failed: {exc}")
    print_admin_commands()


if __name__ == "__main__":
    main()
