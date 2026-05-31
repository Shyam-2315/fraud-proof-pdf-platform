from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = ROOT / "backend" / "app"
ADMIN_FRONTEND_SRC = ROOT / "pdfcraft-guardian-main" / "src"


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

    persist_block = middleware_source.split("await request_log_repository.create_log", 1)[1]
    assert '"request_id": request_id' in persist_block
    assert '"method": request.method' in persist_block
    assert '"path": path' in persist_block
    assert '"status_code": status_code' in persist_block
    assert '"duration_ms": duration_ms' in persist_block
    assert '"client_ip": client_ip' in persist_block
    assert '"block_reason": getattr(request.state, "block_reason", None)' in persist_block
    assert '"fraud_score": getattr(request.state, "fraud_score", None)' in persist_block
    assert "headers" not in persist_block
    assert "cookies" not in persist_block
    assert "body" not in persist_block
    assert "query_params" not in persist_block


def test_admin_frontend_contracts_match_backend_endpoints() -> None:
    admin_api_source = (ADMIN_FRONTEND_SRC / "api" / "adminApi.ts").read_text(encoding="utf-8")
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
