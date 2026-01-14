import pytest

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("DB_HOST", "test-host")
    monkeypatch.setenv("DB_PORT", "9999")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("ETL_DB_USER", "test_user")
    monkeypatch.setenv("ETL_DB_PASSWORD", "test_pass")
    monkeypatch.setenv("APP_DB_PASSWORD", "dummy")