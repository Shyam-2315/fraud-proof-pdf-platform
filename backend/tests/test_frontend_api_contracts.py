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

    identify_index = source.index("await ensureVisitorIdentified();")
    behavior_index = source.index('await sendBehaviorEvent("PAGE_VIEW", { page: "generate" });')
    refresh_index = source.index("await refreshStatus();")
    generate_index = source.index("const result = await generatePdf(values);")

    assert identify_index < behavior_index < refresh_index
    assert source.rfind("await ensureVisitorIdentified();", 0, generate_index) != -1


def test_generate_page_uses_normalized_remaining_for_blocked_state() -> None:
    _require_frontend_source()
    page_source = (FRONTEND_SRC / "pages" / "GeneratePage.tsx").read_text(encoding="utf-8")
    usage_page_source = (FRONTEND_SRC / "pages" / "UsagePage.tsx").read_text(encoding="utf-8")
    usage_card_source = (FRONTEND_SRC / "components" / "UsageCard.tsx").read_text(encoding="utf-8")
    usage_api_source = (FRONTEND_SRC / "api" / "userApi.ts").read_text(encoding="utf-8")

    assert "isVisitorStatusBlocked(status)" in page_source
    assert "isVisitorLimitReached(status)" in page_source
    assert "getVisitorStatusMessage(status)" in page_source
    assert "showLoginCta={!isAuthenticated && isVisitorLimitReached(status)}" in page_source
    assert "showLoginCta={isVisitorLimitReached(status)}" in usage_page_source
    assert "isVisitorSecurityBlocked(status)" in usage_card_source
    assert "const { remaining } = getVisitorUsageSnapshot(status);" in usage_api_source
    assert "limit_reached?: boolean;" in usage_api_source
    assert "return isVisitorLimitReached(status) || isVisitorSecurityBlocked(status);" in usage_api_source
    assert "return remaining <= 0;" in usage_api_source
    assert "requires_login: limitReached" in usage_api_source


def test_frontend_does_not_show_free_limit_prompt_for_security_blocks() -> None:
    _require_frontend_source()
    page_source = (FRONTEND_SRC / "pages" / "GeneratePage.tsx").read_text(encoding="utf-8")
    usage_api_source = (FRONTEND_SRC / "api" / "userApi.ts").read_text(encoding="utf-8")

    assert "setShowLimitPrompt(isVisitorLimitReached" in page_source
    assert "isVisitorSecurityBlocked(body)" in page_source
    assert "SECURITY_BLOCK_MESSAGE" in usage_api_source
    assert "fraud_blocked?: boolean;" in usage_api_source


def test_frontend_exposes_verify_email_route_and_api_calls() -> None:
    _require_frontend_source()
    auth_api_source = (FRONTEND_SRC / "api" / "authApi.ts").read_text(encoding="utf-8")
    app_source = (FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")
    signup_source = (FRONTEND_SRC / "pages" / "SignupPage.tsx").read_text(encoding="utf-8")
    verify_source = (FRONTEND_SRC / "pages" / "VerifyEmailPage.tsx").read_text(encoding="utf-8")

    assert '/api/auth/verify-email' in auth_api_source
    assert '/api/auth/resend-verification' in auth_api_source
    assert "requires_verification" in auth_api_source
    assert 'path="/verify-email"' in app_source
    assert '/verify-email?email=${encodeURIComponent(response.email)}' in signup_source
    assert "setCooldown(60);" in verify_source


def test_account_usage_contract_includes_billing_period_and_plan_limits() -> None:
    _require_frontend_source()
    auth_api_source = (FRONTEND_SRC / "api" / "authApi.ts").read_text(encoding="utf-8")
    account_card_source = (
        FRONTEND_SRC / "components" / "AccountUsageCard.tsx"
    ).read_text(encoding="utf-8")
    pricing_source = (FRONTEND_SRC / "pages" / "PricingPage.tsx").read_text(encoding="utf-8")

    assert "billing_period_start: string;" in auth_api_source
    assert "billing_period_end: string;" in auth_api_source
    assert "plan_limits: Record<string, number>;" in auth_api_source
    assert "formatDate(usage.billing_period_start)" in account_card_source
    assert "formatDate(usage.billing_period_end)" in account_card_source
    assert "usage.requires_upgrade" in account_card_source
    assert "placeholder" in pricing_source.lower()
