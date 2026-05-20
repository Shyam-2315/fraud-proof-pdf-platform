import os
from pathlib import Path
from uuid import uuid4

import httpx


BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8025").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3025").rstrip("/")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-admin-key")
FORBIDDEN_CUSTOMER_TERMS = (
    "fraud",
    "fingerprint",
    "tracking",
    "risk",
    "suspicious",
    "abuse",
    " ml",
    "visitor investigation",
    "ip monitoring",
    "user-agent",
    "security engine",
)


class CheckRunner:
    def __init__(self) -> None:
        self.failed = 0

    def pass_(self, label: str, detail: str = "") -> None:
        print(f"PASS  {label}{': ' + detail if detail else ''}")

    def fail(self, label: str, detail: str) -> None:
        self.failed += 1
        print(f"FAIL  {label}: {detail}")

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.pass_(label, detail)
        else:
            self.fail(label, detail or "condition was false")


def main() -> None:
    runner = CheckRunner()
    prefix = f"final-demo-{uuid4()}"
    ip_suffix = uuid4().int % 200 + 1
    headers = {
        "X-Forwarded-For": f"198.18.{ip_suffix}.10",
        "User-Agent": f"PDFCraftFinalDemo/{prefix}",
    }

    with httpx.Client(base_url=BACKEND_PUBLIC_URL, timeout=15.0, headers=headers) as client:
        health = safe_request(lambda: client.get("/health"))
        runner.check("Backend health endpoint", health is not None and health.status_code == 200, response_detail(health))

        config = safe_request(lambda: client.get("/api/public/config"))
        runner.check(
            "Public config endpoint",
            config is not None and config.status_code == 200 and config.json().get("product_name") == "PDFCraft",
            response_detail(config),
        )

        frontend_response, frontend_url = check_frontend()
        runner.check(
            "Frontend reachable",
            frontend_response is not None and frontend_response.status_code == 200,
            f"{frontend_url} -> {response_detail(frontend_response)}",
        )

        identify = safe_request(lambda: client.post("/api/visitor/identify", json=visitor_payload(prefix)))
        identify_ok = identify is not None and identify.status_code == 200 and customer_safe(identify.json())
        runner.check("Anonymous visitor identify", identify_ok, response_detail(identify))

        pdf1 = safe_request(lambda: client.post("/api/pdf/generate", json=pdf_payload("PDF 1")))
        runner.check("Anonymous PDF 1 generation", pdf_success(pdf1), response_detail(pdf1))

        pdf2 = safe_request(lambda: client.post("/api/pdf/generate", json=pdf_payload("PDF 2")))
        runner.check("Anonymous PDF 2 generation", pdf_success(pdf2), response_detail(pdf2))

        pdf3 = safe_request(lambda: client.post("/api/pdf/generate", json=pdf_payload("PDF 3")))
        pdf3_body = json_body(pdf3)
        runner.check(
            "Anonymous PDF 3 requires login with safe message",
            pdf3 is not None
            and pdf3.status_code == 403
            and pdf3_body.get("message") == "Please log in to continue."
            and pdf3_body.get("requires_login") is True
            and customer_safe(pdf3_body),
            response_detail(pdf3),
        )

        history = safe_request(lambda: client.get("/api/pdf/my-history"))
        history_body = json_body(history)
        runner.check(
            "Customer history returns two successful PDFs",
            history is not None and history.status_code == 200 and history_body.get("total") == 2,
            response_detail(history),
        )

        admin_headers = {"X-Admin-API-Key": ADMIN_API_KEY}
        summary = safe_request(lambda: client.get("/api/admin/fraud/summary", headers=admin_headers))
        runner.check("Admin summary endpoint with API key", summary is not None and summary.status_code == 200, response_detail(summary))

        models = safe_request(lambda: client.get("/api/admin/ml/models", headers=admin_headers))
        models_body = json_body(models)
        runner.check("Admin ML models endpoint with API key", models is not None and models.status_code == 200, response_detail(models))

        dataset_path = Path("data/synthetic_fraud_dataset.csv")
        runner.check(
            "Synthetic dataset file",
            dataset_path.exists(),
            "present" if dataset_path.exists() else "run python scripts/generate_synthetic_fraud_dataset.py",
        )

        active = safe_request(lambda: client.get("/api/admin/ml/models/active", headers=admin_headers))
        active_body = json_body(active)
        model_count = int(models_body.get("total", len(models_body.get("items", []))) or 0)
        active_version = active_body.get("active_model", {}).get("version") if isinstance(active_body.get("active_model"), dict) else None
        runner.check(
            "Active/candidate model status",
            active is not None and active.status_code == 200,
            f"active={active_version or 'none'}, versions={model_count}",
        )

    if runner.failed:
        print(f"\nFinal demo check completed with {runner.failed} failure(s).")
        raise SystemExit(1)
    print("\nFinal demo check passed.")


def check_frontend() -> tuple[httpx.Response | None, str]:
    urls = [FRONTEND_URL]
    if FRONTEND_URL in {"http://localhost:3025", "http://127.0.0.1:3025"}:
        urls.append("http://frontend:3025")
    for url in urls:
        response = safe_request(lambda url=url: httpx.get(url, timeout=5.0))
        if response is not None and response.status_code == 200:
            return response, url
    return None, urls[-1]


def visitor_payload(prefix: str) -> dict:
    return {
        "local_storage_id": f"{prefix}-local",
        "session_id": f"{prefix}-session",
        "fingerprint_hash": f"{prefix}-fingerprint",
        "device_profile_hash": f"{prefix}-device",
        "canvas_hash": f"{prefix}-canvas",
        "webgl_hash": f"{prefix}-webgl",
        "audio_hash": f"{prefix}-audio",
        "device_info": {
            "screen": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux",
        },
        "automation_signals": {
            "webdriver": False,
            "plugins_count": 5,
            "cookies_enabled": True,
            "local_storage_available": True,
            "session_storage_available": True,
        },
    }


def pdf_payload(title: str) -> dict:
    return {"title": title, "content": f"{title} generated by final demo check."}


def pdf_success(response: httpx.Response | None) -> bool:
    body = json_body(response)
    return response is not None and response.status_code == 200 and bool(body.get("pdf_id")) and customer_safe(body)


def customer_safe(body: object) -> bool:
    text = str(body).lower()
    return not any(term in text for term in FORBIDDEN_CUSTOMER_TERMS)


def json_body(response: httpx.Response | None) -> dict:
    if response is None:
        return {}
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def response_detail(response: httpx.Response | None) -> str:
    if response is None:
        return "no response"
    text = response.text.replace("\n", " ")
    if len(text) > 180:
        text = text[:177] + "..."
    return f"HTTP {response.status_code} {text}"


def safe_request(callback):
    try:
        return callback()
    except Exception:
        return None


if __name__ == "__main__":
    main()
