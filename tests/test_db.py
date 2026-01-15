# tests/test_db.py
import psycopg
import pytest

from transit_core.config import get_settings


def test_database_connection():
    """
    Integration test. No 'mock_env' requested, so it
    uses your real .env file automatically.
    """
    # Force a cache clear just in case a previous test ran mock_env
    get_settings.cache_clear()

    settings = get_settings()
    conn_info = settings.etl_database_url

    try:
        with psycopg.connect(conn_info) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                assert cur.fetchone()[0] == 1
    except Exception as e:
        pytest.fail(f"Database connection failed. host={settings.db_host}: {e}")
