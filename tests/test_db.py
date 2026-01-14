import psycopg
import pytest
from transit_core.config import Settings

def test_database_connection():
    real_settings = Settings() 
    conn_info = real_settings.etl_database_url
    
    try:
        with psycopg.connect(conn_info) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                assert cur.fetchone()[0] == 1
    except Exception as e:
        pytest.fail(f"Database connection failed. Ensure Postgres is running: {e}")