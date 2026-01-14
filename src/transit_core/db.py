from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import logging
import time

logger = logging.getLogger(__name__)

def create_db_pool(connection_url: str):
    """
    Creates the connection pool
    """
    pool = ConnectionPool(
        conninfo=connection_url,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row}
    )
    return pool

def wait_for_db(pool):
    retries = 5
    retry_count = 0
    while retry_count < retries:
        try:
            with pool.connection() as conn:
                conn.execute("SELECT 1")
            logger.info("Database is ready.")
            return
        except Exception as e:
            logger.warning(f"Database is not ready. {retries} retries remaining.")
            retry_count += 1
            time.sleep(2)
    raise Exception(f"Could not connect to database after {retries} attempts.")