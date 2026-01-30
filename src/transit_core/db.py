import logging
import time

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


def create_db_pool(connection_url: str):
    """
    Creates the connection pool
    """
    masked_url = connection_url.split("@")[-1] if "@" in connection_url else "..."
    logger.info(f"Creating DB connection pool for {masked_url}")
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
            logger.info(f"Database is ready. Waited {time.time() - start_wait:.2f}s")
            return
        except Exception:
            logger.warning(f"Database is not ready. {retries} retries remaining.")
            retry_count += 1
            time.sleep(2)
    raise Exception(f"Could not connect to database after {retries} attempts.")
