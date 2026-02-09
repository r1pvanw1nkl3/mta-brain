from unittest.mock import MagicMock, patch

import pytest

from transit_core.config import get_settings
from transit_core.core.exceptions import DatabaseError
from transit_core.db import create_db_pool, wait_for_db


def test_database_connection():
    """
    Integration test. Uses the real .env file and transit_core.db.
    """
    get_settings.cache_clear()
    settings = get_settings()

    pool = create_db_pool(settings.etl_database_url)
    try:
        wait_for_db(pool)
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as val")
                row = cur.fetchone()
                assert row["val"] == 1
    finally:
        pool.close()


def test_wait_for_db_retry_success():
    mock_pool = MagicMock()
    mock_conn = MagicMock()

    # Fail once, then succeed
    mock_pool.connection.return_value.__enter__.side_effect = [
        Exception("DB Not Ready"),
        mock_conn,
    ]

    with patch("time.sleep"):  # Don't actually sleep
        wait_for_db(mock_pool)

    assert mock_pool.connection.call_count == 2


def test_wait_for_db_exhausted_retries():
    mock_pool = MagicMock()
    mock_pool.connection.return_value.__enter__.side_effect = Exception(
        "Persistent Error"
    )

    with patch("time.sleep"), pytest.raises(DatabaseError):
        wait_for_db(mock_pool)

    assert mock_pool.connection.call_count == 5
