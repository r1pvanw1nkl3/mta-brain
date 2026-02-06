import csv
import logging
from typing import IO, Dict

from psycopg import Connection, Cursor

logger = logging.getLogger(__name__)

GTFS_TABLES = [
    "agency",
    "stops",
    "routes",
    "shapes",
    "calendar",
    "trips",
    "stop_times",
    "transfers",
]


def truncate_tables(conn: Connection, schema: str = "public"):
    tables_with_schema = [f"{schema}.{t}" for t in GTFS_TABLES]
    tables_sql = ", ".join(tables_with_schema)
    with conn.cursor() as cur:
        logger.info(
            "Truncating tables", extra={"schema": schema, "tables": GTFS_TABLES}
        )
        cur.execute(f"TRUNCATE {tables_sql} CASCADE")


def load_table(cur: Cursor, table_name: str, file_obj: IO, schema: str):
    headers = file_obj.readline()

    if not headers:
        logger.warning(
            "No rows found for table",
            extra={"table_name": table_name, "schema": schema},
        )

    reader = csv.reader([headers])
    columns = next(reader)

    columns = [c.strip().replace("\ufeff", "") for c in columns]

    clean_columns = []
    for col in columns:
        if not col.replace("_", "").isalnum():
            raise ValueError(f"Unsafe column name detected in {table_name}: {col}")
        clean_columns.append(col)

    columns_sql = ", ".join(clean_columns)

    sql = (
        f"COPY {schema}.{table_name} ({columns_sql}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER FALSE)"
    )

    with cur.copy(sql) as copy:
        while data := file_obj.read(8192):
            copy.write(data)


def load_all(conn: Connection, data_map: Dict[str, IO], schema: str):
    from transit_core.core.exceptions import DatabaseError

    with conn.transaction():
        truncate_tables(conn, schema)
        for table_name in GTFS_TABLES:
            if table_name in data_map:
                try:
                    logger.info(
                        "Loading table",
                        extra={"table_name": table_name, "schema": schema},
                    )
                    with conn.cursor() as cur:
                        load_table(cur, table_name, data_map[table_name], schema)
                except Exception as e:
                    logger.exception(
                        "Error occurred during load of table",
                        extra={"table_name": table_name, "schema": schema},
                    )
                    raise DatabaseError(
                        f"Failed to load table {table_name}: {e}"
                    ) from e
