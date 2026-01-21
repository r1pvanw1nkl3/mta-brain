import pytest

from transit_core.config import get_settings


@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("DB_HOST", "test-host")
    monkeypatch.setenv("DB_PORT", "9999")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("ETL_DB_USER", "test_user")
    monkeypatch.setenv("ETL_DB_PASSWORD", "test_pass")
    monkeypatch.setenv("APP_DB_PASSWORD", "dummy")
    monkeypatch.setenv("APP_DB_USER", "test_user")

    get_settings.cache_clear()

    return get_settings()
