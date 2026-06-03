from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
BACKEND_APP = BACKEND_ROOT / "app"
ADMIN_FRONTEND_SRC = REPO_ROOT / "pdfcraft-guardian-main" / "src"


def test_admin_monitoring_routes_are_protected_and_versioned() -> None:
    route_source = (BACKEND_APP / "routes" / "admin_fraud.py").read_text(encoding="utf-8")

    assert "dependencies=[Depends(require_admin_api_key)]" in route_source
    assert '"/monitoring"' in route_source
    assert '"/logs"' in route_source
    assert '"/users"' in route_source
    assert '"/users/{user_id}/block"' in route_source
    assert '"/users/{user_id}/unblock"' in route_source
    assert "AdminMonitoringResponse" in route_source
    assert "AdminRequestLogListResponse" in route_source
    assert "AdminUserManagementListResponse" in route_source


def test_request_log_collection_is_sanitized_metadata_only() -> None:
    middleware_source = (BACKEND_APP / "core" / "middleware.py").read_text(encoding="utf-8")

    persist_block = middleware_source.split("await request_log_repository.create_log(", 1)[1]
    payload_block = persist_block.split(")\n", 1)[0]
    assert "sanitize_log_value" in middleware_source
    assert '"request_id": sanitize_log_value(request_id)' in payload_block
    assert '"method": sanitize_log_value(request.method)' in payload_block
    assert '"path": path' in payload_block
    assert '"status_code": status_code' in payload_block
    assert '"duration_ms": duration_ms' in payload_block
    assert '"client_ip": sanitize_log_value(client_ip)' in payload_block
    assert '"block_reason": sanitize_log_value(getattr(request.state, "block_reason", None))' in payload_block
    assert '"fraud_score": getattr(request.state, "fraud_score", None)' in payload_block
    assert '"headers":' not in payload_block
    assert '"cookies":' not in payload_block
    assert '"body":' not in payload_block
    assert '"query_params":' not in payload_block
    assert "authorization" not in payload_block.lower()
    assert "cookie" not in payload_block.lower()


def test_admin_frontend_contracts_match_backend_endpoints() -> None:
    admin_api_path = ADMIN_FRONTEND_SRC / "api" / "adminApi.ts"
    if not admin_api_path.exists():
        pytest.skip("Admin frontend source is not mounted in this backend test environment.")

    admin_api_source = admin_api_path.read_text(encoding="utf-8")
    layout_source = (
        ADMIN_FRONTEND_SRC / "components" / "admin" / "AdminLayout.tsx"
    ).read_text(encoding="utf-8")

    assert "/api/admin/monitoring" in admin_api_source
    assert "/api/admin/logs" in admin_api_source
    assert "/api/admin/users" in admin_api_source
    assert "/api/admin/fraud/decisions" in admin_api_source
    assert "AdminMonitoringResponse" in admin_api_source
    assert "AdminRequestLogListResponse" in admin_api_source
    assert "AdminFraudDecisionListResponse" in admin_api_source
    assert "AdminUserManagementListResponse" in admin_api_source
    assert '"/admin/monitoring"' in layout_source
    assert '"/admin/logs"' in layout_source
    assert '"/admin/fraud-decisions"' in layout_source
    assert '"/admin/users"' in layout_source
