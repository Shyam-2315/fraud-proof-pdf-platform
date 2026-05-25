import os

from app.config import get_settings


TEST_MONGO_URL = (
    os.getenv("TEST_MONGO_URL")
    or os.getenv("MONGODB_URL")
    or os.getenv("MONGO_URL")
    or "mongodb://localhost:27225"
)
TEST_MONGO_DB_NAME = (
    os.getenv("TEST_MONGO_DB_NAME")
    or os.getenv("MONGODB_DB_NAME")
    or os.getenv("MONGO_DB_NAME")
    or "fraud_pdf"
)

PRODUCTION_TEST_ENV = {
    "FRONTEND_URL": "https://pdfcraft.example.com",
    "ADMIN_FRONTEND_URL": "https://admin.pdfcraft.example.com",
    "BACKEND_PUBLIC_URL": "https://api.pdfcraft.example.com",
    "CORS_ORIGINS": '["https://pdfcraft.example.com","https://admin.pdfcraft.example.com"]',
    "JWT_SECRET_KEY": "test-strong-production-secret-not-default",
    "ADMIN_API_KEY": "test-strong-admin-key-not-default",
    "DEFAULT_ADMIN_PASSWORD": "TestStrongAdminPassword123",
    "ENABLE_DEFAULT_ADMIN_SEED": "false",
    "SECURE_COOKIES": "true",
}


def apply_test_env(monkeypatch, **values: str) -> None:
    env_values = dict(PRODUCTION_TEST_ENV if values.get("APP_ENV") == "production" else {})
    env_values.update(values)
    env_values.setdefault("JWT_SECRET_KEY", "test-secret-value-that-is-long-enough")
    env_values.setdefault("ADMIN_API_KEY", "test-admin-key-that-is-long-enough")
    env_values.setdefault("SECURE_COOKIES", "true")
    env_values.setdefault("ENABLE_DEFAULT_ADMIN_SEED", "false")

    for key, value in env_values.items():
        monkeypatch.setenv(key, value)

    get_settings.cache_clear()
