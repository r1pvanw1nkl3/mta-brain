import logging
import time

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from transit_core.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


def create_db_pool(connection_url: str):
    """
    Creates the connection pool
    """
    masked_url = connection_url.split("@")[-1] if "@" in connection_url else "..."
    logger.info("Creating DB connection pool", extra={"db_host": masked_url})
    pool = ConnectionPool(
        conninfo=connection_url,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row, "connect_timeout": 5},
        open=True,
    )
    return pool


def wait_for_db(pool):
    retries = 5
    retry_count = 0
    start_wait = time.time()
    while retry_count < retries:
        try:
            with pool.connection() as conn:
                conn.execute("SELECT 1")
            elapsed = time.time() - start_wait
            logger.info(
                "Database is ready", extra={"wait_time_seconds": round(elapsed, 2)}
            )
            return
        except Exception as e:
            logger.warning(
                "Database is not ready, retrying",
                extra={
                    "retry_count": retry_count + 1,
                    "max_retries": retries,
                    "error": str(e),
                },
            )
            retry_count += 1
            time.sleep(2)
    raise DatabaseError(f"Could not connect to database after {retries} attempts.")
