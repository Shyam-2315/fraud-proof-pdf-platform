from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"


def _require_frontend_source() -> None:
    if not FRONTEND_SRC.exists():
        pytest.skip("Frontend source tree is not available in this runtime.")


def test_api_url_uses_configured_render_backend_and_normalizes_slashes() -> None:
    _require_frontend_source()
    client_source = (FRONTEND_SRC / "api" / "client.ts").read_text(encoding="utf-8")

    assert 'import.meta.env.VITE_API_BASE_URL || "http://localhost:8025"' in client_source
    assert 'const cleanBase = API_BASE_URL.replace(/\\/$/, "");' in client_source
    assert 'const cleanPath = path.startsWith("/") ? path : `/${path}`;' in client_source
    assert "return `${cleanBase}${cleanPath}`;" in client_source


def test_frontend_does_not_use_relative_or_broken_production_api_paths() -> None:
    _require_frontend_source()
    source_files = [
        FRONTEND_SRC / "api" / "client.ts",
        FRONTEND_SRC / "api" / "userApi.ts",
        FRONTEND_SRC / "pages" / "GeneratePage.tsx",
        FRONTEND_SRC / "components" / "PdfHistoryTable.tsx",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_files)

    assert 'fetch("/api/' not in combined_source
    assert "fetch('/api/" not in combined_source
    assert "//api/" not in combined_source
    assert "/production/api/" not in combined_source
    assert "pdfcraft-customer.vercel.app/api/" not in combined_source


def test_generate_page_identifies_before_status_and_before_generate() -> None:
    _require_frontend_source()
    source = (FRONTEND_SRC / "pages" / "GeneratePage.tsx").read_text(encoding="utf-8")

    assert source.index("await ensureVisitorIdentified();\n        await sendBehaviorEvent") < source.index("await refreshStatus();")
    assert "await ensureVisitorIdentified();\n      const result = await generatePdf(values);" in source


def test_frontend_exposes_verify_email_route_and_api_calls() -> None:
    _require_frontend_source()
    auth_api_source = (FRONTEND_SRC / "api" / "authApi.ts").read_text(encoding="utf-8")
    app_source = (FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")

    assert '/api/auth/verify-email' in auth_api_source
    assert '/api/auth/resend-verification' in auth_api_source
    assert 'path="/verify-email"' in app_source
