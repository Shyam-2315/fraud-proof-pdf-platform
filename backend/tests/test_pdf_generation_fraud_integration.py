import os
from uuid import uuid4

import httpx
from pymongo import MongoClient

from conftest import TEST_MONGO_DB_NAME, TEST_MONGO_URL


BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8025")
RUN_IP_SEGMENT = uuid4().int % 200 + 1

CUSTOMER_FORBIDDEN = {
    "fraud",
    "risk",
    "fingerprint",
    "tracked_signals",
    "matched_signals",
    "model_version",
    "fraud_probability",
    "anomaly_score",
    "rule_score",
    "ip_address",
    "user_agent",
    "block_reason",
    "FREE_LIMIT_REACHED",
    "CRITICAL_RISK",
}


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid4()}@example.com"


def _headers(ip_suffix: int, user_agent: str | None = None) -> dict[str, str]:
    return {
        "X-Forwarded-For": f"198.51.{RUN_IP_SEGMENT}.{ip_suffix}",
        "User-Agent": user_agent or f"PDFCraftTest/{uuid4()}",
    }


def _identity_headers(
    ip_address: str,
    visitor_id: str,
    session_id: str,
    fingerprint_hash: str,
    user_agent: str | None = None,
) -> dict[str, str]:
    return {
        "X-Forwarded-For": ip_address,
        "User-Agent": user_agent or f"PDFCraftTest/{uuid4()}",
        "X-Anon-Id": visitor_id,
        "X-Visitor-Id": visitor_id,
        "X-Session-Id": session_id,
        "X-Device-Fingerprint": fingerprint_hash,
    }


def _payload(
    prefix: str,
    *,
    local_storage_id: str | None = None,
    session_id: str | None = None,
    fingerprint_hash: str | None = None,
) -> dict:
    return {
        "local_storage_id": local_storage_id or f"{prefix}-local",
        "session_id": session_id or f"{prefix}-session",
        "fingerprint_hash": fingerprint_hash or f"{prefix}-fingerprint",
        "device_profile_hash": f"{prefix}-device",
        "canvas_hash": f"{prefix}-canvas",
        "webgl_hash": f"{prefix}-webgl",
        "audio_hash": f"{prefix}-audio",
        "device_info": {
            "screen": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux",
            "hardware_concurrency": 8,
            "device_memory": 8,
            "touch_support": 0,
        },
        "automation_signals": {
            "webdriver": False,
            "plugins_count": 5,
            "cookies_enabled": True,
            "local_storage_available": True,
            "session_storage_available": True,
        },
    }


def _identify(client: httpx.Client, prefix: str, **kwargs: str) -> dict:
    response = client.post("/api/visitor/identify", json=_payload(prefix, **kwargs))
    assert response.status_code == 200, response.text
    body = response.json()
    _assert_customer_safe(body)
    return body


def _generate(client: httpx.Client, title: str) -> httpx.Response:
    return client.post(
        "/api/pdf/generate",
        json={"title": title, "content": f"{title} body"},
    )


def _assert_customer_safe(body: dict) -> None:
    serialized = str(body).lower()
    for forbidden in CUSTOMER_FORBIDDEN:
        assert forbidden.lower() not in serialized


def test_anonymous_first_and_second_pdfs_allowed_and_download_works() -> None:
    prefix = f"anon-two-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(21)) as client:
        _identify(client, prefix)

        first = _generate(client, "Anon first")
        assert first.status_code == 200, first.text
        first_body = first.json()
        _assert_customer_safe(first_body)
        assert first_body["used"] == 1
        assert first_body["remaining"] == 1
        assert first_body["free_usage_count"] == 1
        assert first_body["remaining_free_uses"] == 1
        assert first_body["pdf_id"]

        second = _generate(client, "Anon second")
        assert second.status_code == 200, second.text
        second_body = second.json()
        _assert_customer_safe(second_body)
        assert second_body["used"] == 2
        assert second_body["remaining"] == 0
        assert second_body["free_usage_count"] == 2
        assert second_body["remaining_free_uses"] == 0

        download = client.get(f"/api/pdf/download/{second_body['pdf_id']}")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/pdf")


def test_anonymous_third_pdf_requires_login_with_clean_response() -> None:
    prefix = f"anon-third-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(22)) as client:
        _identify(client, prefix)
        assert _generate(client, "Anon one").status_code == 200
        assert _generate(client, "Anon two").status_code == 200

        third = _generate(client, "Anon three")
        assert third.status_code == 403
        assert third.json() == {
            "success": False,
            "message": "Please log in to continue.",
            "requires_login": True,
        }
        _assert_customer_safe(third.json())


def test_same_fingerprint_changed_cookie_does_not_reset_limit() -> None:
    prefix = f"changed-cookie-{uuid4()}"
    fingerprint_hash = f"{prefix}-shared-fingerprint"

    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(23)) as first:
        first_identify = _identify(first, prefix, fingerprint_hash=fingerprint_hash)
        assert _generate(first, "Cookie one").status_code == 200
        assert _generate(first, "Cookie two").status_code == 200

    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(24)) as second:
        second_identify = _identify(
            second,
            f"{prefix}-new",
            local_storage_id=f"{prefix}-new-local",
            session_id=f"{prefix}-new-session",
            fingerprint_hash=fingerprint_hash,
        )
        assert second_identify["visitor_id"] == first_identify["visitor_id"]
        blocked = _generate(second, "Cookie three")
        assert blocked.status_code == 403
        assert blocked.json()["requires_login"] is True


def test_changed_ip_does_not_reset_anonymous_limit() -> None:
    prefix = f"changed-ip-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(25)) as client:
        _identify(client, prefix)
        assert _generate(client, "IP one").status_code == 200
        assert _generate(client, "IP two").status_code == 200
        changed_ip = client.post(
            "/api/pdf/generate",
            headers=_headers(26),
            json={"title": "IP three", "content": "IP three body"},
        )
        assert changed_ip.status_code == 403
        assert changed_ip.json()["requires_login"] is True


def test_same_ip_only_does_not_merge_different_users() -> None:
    ip = 27
    first_prefix = f"same-ip-a-{uuid4()}"
    second_prefix = f"same-ip-b-{uuid4()}"

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_headers(ip, "PDFCraftSameIP/A"),
    ) as first:
        first_identify = _identify(first, first_prefix)
        first_status = first.get("/api/visitor/status")
        assert first_status.status_code == 200

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_headers(ip, "PDFCraftSameIP/B"),
    ) as second:
        second_identify = _identify(second, second_prefix)
        second_status = second.get("/api/visitor/status")
        assert second_status.status_code == 200

    assert first_identify["visitor_id"] != second_identify["visitor_id"]
    assert first_status.json()["remaining_free_uses"] == 2
    assert second_status.json()["remaining_free_uses"] == 2


def test_shared_ip_status_syncs_across_new_visitors() -> None:
    ip_address = "203.0.113.50"
    first_prefix = f"shared-ip-a-{uuid4()}"
    second_prefix = f"shared-ip-b-{uuid4()}"

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            ip_address,
            f"{first_prefix}-local",
            f"{first_prefix}-session",
            f"{first_prefix}-fingerprint",
        ),
    ) as first:
        _identify(
            first,
            first_prefix,
            local_storage_id=f"{first_prefix}-local",
            session_id=f"{first_prefix}-session",
            fingerprint_hash=f"{first_prefix}-fingerprint",
        )
        first_generate = _generate(first, "Shared IP first")
        assert first_generate.status_code == 200, first_generate.text
        assert first_generate.json()["free_usage_count"] == 1

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            ip_address,
            f"{second_prefix}-local",
            f"{second_prefix}-session",
            f"{second_prefix}-fingerprint",
        ),
    ) as second:
        _identify(
            second,
            second_prefix,
            local_storage_id=f"{second_prefix}-local",
            session_id=f"{second_prefix}-session",
            fingerprint_hash=f"{second_prefix}-fingerprint",
        )
        status_response = second.get("/api/visitor/status")
        assert status_response.status_code == 200, status_response.text
        body = status_response.json()
        _assert_customer_safe(body)
        assert body["free_usage_count"] == 1
        assert body["free_usage_limit"] == 2
        assert body["remaining_free_uses"] == 1
        assert body["requires_login"] is False


def test_shared_ip_second_pdf_from_new_visitor_reaches_limit_for_all_browsers() -> None:
    ip_address = "203.0.113.51"
    chrome_prefix = f"shared-limit-a-{uuid4()}"
    incognito_prefix = f"shared-limit-b-{uuid4()}"
    safari_prefix = f"shared-limit-c-{uuid4()}"

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            ip_address,
            f"{chrome_prefix}-local",
            f"{chrome_prefix}-session",
            f"{chrome_prefix}-fingerprint",
        ),
    ) as chrome:
        _identify(
            chrome,
            chrome_prefix,
            local_storage_id=f"{chrome_prefix}-local",
            session_id=f"{chrome_prefix}-session",
            fingerprint_hash=f"{chrome_prefix}-fingerprint",
        )
        first_generate = _generate(chrome, "Shared limit first")
        assert first_generate.status_code == 200, first_generate.text
        second_generate = _generate(chrome, "Shared limit second")
        assert second_generate.status_code == 200, second_generate.text
        chrome_body = second_generate.json()
        _assert_customer_safe(chrome_body)
        assert chrome_body["free_usage_count"] == 2
        assert chrome_body["remaining_free_uses"] == 0

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            ip_address,
            f"{incognito_prefix}-local",
            f"{incognito_prefix}-session",
            f"{incognito_prefix}-fingerprint",
        ),
    ) as incognito:
        _identify(
            incognito,
            incognito_prefix,
            local_storage_id=f"{incognito_prefix}-local",
            session_id=f"{incognito_prefix}-session",
            fingerprint_hash=f"{incognito_prefix}-fingerprint",
        )
        status_response = incognito.get("/api/visitor/status")
        assert status_response.status_code == 200, status_response.text
        body = status_response.json()
        _assert_customer_safe(body)
        assert body["free_usage_count"] == 2
        assert body["remaining_free_uses"] == 0
        assert body["is_blocked"] is True
        assert body["requires_login"] is True

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            ip_address,
            f"{safari_prefix}-local",
            f"{safari_prefix}-session",
            f"{safari_prefix}-fingerprint",
        ),
    ) as safari:
        _identify(
            safari,
            safari_prefix,
            local_storage_id=f"{safari_prefix}-local",
            session_id=f"{safari_prefix}-session",
            fingerprint_hash=f"{safari_prefix}-fingerprint",
        )
        status_response = safari.get("/api/visitor/status")
        assert status_response.status_code == 200, status_response.text
        body = status_response.json()
        _assert_customer_safe(body)
        assert body["free_usage_count"] == 2
        assert body["remaining_free_uses"] == 0
        assert body["is_blocked"] is True
        assert body["requires_login"] is True


def test_shared_ip_third_new_visitor_is_blocked() -> None:
    ip_address = "203.0.113.52"
    prefixes = [f"shared-block-{uuid4()}-{index}" for index in range(3)]

    for index, prefix in enumerate(prefixes):
        with httpx.Client(
            base_url=BASE_URL,
            timeout=10.0,
            headers=_identity_headers(
                ip_address,
                f"{prefix}-local",
                f"{prefix}-session",
                f"{prefix}-fingerprint",
            ),
        ) as client:
            _identify(
                client,
                prefix,
                local_storage_id=f"{prefix}-local",
                session_id=f"{prefix}-session",
                fingerprint_hash=f"{prefix}-fingerprint",
            )
            response = _generate(client, f"Shared blocked {index}")
            if index < 2:
                assert response.status_code == 200, response.text
            else:
                assert response.status_code == 403
                assert response.json() == {
                    "success": False,
                    "message": "Free limit reached. Please log in to continue.",
                    "requires_login": True,
                }
                _assert_customer_safe(response.json())


def test_different_ip_gets_separate_shared_quota() -> None:
    first_prefix = f"separate-ip-a-{uuid4()}"
    second_prefix = f"separate-ip-b-{uuid4()}"

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            "203.0.113.60",
            f"{first_prefix}-local",
            f"{first_prefix}-session",
            f"{first_prefix}-fingerprint",
        ),
    ) as first:
        _identify(
            first,
            first_prefix,
            local_storage_id=f"{first_prefix}-local",
            session_id=f"{first_prefix}-session",
            fingerprint_hash=f"{first_prefix}-fingerprint",
        )
        assert _generate(first, "Separate IP first").status_code == 200

    with httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
        headers=_identity_headers(
            "203.0.113.61",
            f"{second_prefix}-local",
            f"{second_prefix}-session",
            f"{second_prefix}-fingerprint",
        ),
    ) as second:
        _identify(
            second,
            second_prefix,
            local_storage_id=f"{second_prefix}-local",
            session_id=f"{second_prefix}-session",
            fingerprint_hash=f"{second_prefix}-fingerprint",
        )
        status_response = second.get("/api/visitor/status")
        assert status_response.status_code == 200, status_response.text
        body = status_response.json()
        _assert_customer_safe(body)
        assert body["free_usage_count"] == 0
        assert body["remaining_free_uses"] == 2


def test_logged_in_user_can_generate_after_anonymous_block() -> None:
    prefix = f"login-after-block-{uuid4()}"
    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(28)) as client:
        _identify(client, prefix)
        assert _generate(client, "Before login one").status_code == 200
        assert _generate(client, "Before login two").status_code == 200
        assert _generate(client, "Before login three").status_code == 403

        register = client.post(
            "/api/auth/register",
            json={
                "email": _email("after-block"),
                "full_name": "After Block",
                "password": "StrongPassword123",
            },
        )
        assert register.status_code == 200, register.text
        token = register.json()["access_token"]

        authed = client.post(
            "/api/pdf/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Logged in PDF", "content": "Logged in body"},
        )
        assert authed.status_code == 200, authed.text
        body = authed.json()
        _assert_customer_safe(body)
        assert body["plan"] == "FREE"
        assert body["limit"] == 5
        assert body["used"] == 1


def test_generate_attempt_stores_fraud_engine_records() -> None:
    prefix = f"engine-records-{uuid4()}"
    mongo = MongoClient(TEST_MONGO_URL)
    db = mongo[TEST_MONGO_DB_NAME]

    with httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers(29)) as client:
        identify = _identify(client, prefix)
        response = _generate(client, "Engine record PDF")
        assert response.status_code == 200, response.text

    visitor_id = identify["visitor_id"]
    assert db.fraud_feature_snapshots.count_documents(
        {"visitor_id": visitor_id, "action_type": "PDF_GENERATE_ATTEMPT"}
    ) >= 1
    assert db.fraud_decisions.count_documents(
        {"visitor_id": visitor_id, "action_type": "PDF_GENERATE_ATTEMPT"}
    ) >= 1
    assert db.risk_score_snapshots.count_documents({"visitor_id": visitor_id}) >= 1
    assert db.fraud_training_events.count_documents(
        {"visitor_id": visitor_id, "action_type": "PDF_GENERATE_ATTEMPT"}
    ) >= 1
