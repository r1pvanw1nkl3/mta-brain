import csv
import io
import logging

import psycopg
import requests
from psycopg.rows import DictRow, dict_row

from transit_core.config import get_settings
from transit_core.transit_core_logging import setup_logging

logger = logging.getLogger(__name__)


def load_entrances():
    settings = get_settings()
    setup_logging(settings.etl_log_file_path)

    logger.info("Downloading MTA Entrance data from %s", settings.subway_entrances_url)
    response = requests.get(settings.subway_entrances_url)
    response.raise_for_status()

    # Use io.StringIO to treat the downloaded text as a file
    f = io.StringIO(response.text)
    reader = csv.DictReader(f)

    # 2. Connect to Postgres
    # We use DictRow to match the project's preferred connection type
    with psycopg.Connection[DictRow].connect(
        settings.etl_database_url, row_factory=dict_row
    ) as conn:
        with conn.cursor() as cur:
            # Clear existing data to avoid duplicates
            logger.info("Truncating subway_entrances table...")
            cur.execute("TRUNCATE TABLE subway_entrances;")

            # 3. High-Speed COPY
            # We stream the data directly into Postgres
            logger.info("Streaming data to Postgres via COPY...")
            copy_sql = (
                "COPY subway_entrances ("
                "division, line, borough, stop_name, complex_id, "
                "constituent_station_name, station_id, gtfs_stop_id, "
                "daytime_routes, entrance_type, entry_allowed, exit_allowed, "
                "entrance_latitude, entrance_longitude"
                ") FROM STDIN"
            )
            with cur.copy(copy_sql) as copy:
                for row in reader:
                    # Clean Boolean values (YES/NO -> True/False)
                    def to_bool(val: str) -> bool:
                        if not val:
                            return False
                        return val.strip().upper() == "YES"

                    copy.write_row(
                        (
                            row["Division"],
                            row["Line"],
                            row["Borough"],
                            row["Stop Name"],
                            row["Complex ID"],
                            row["Constituent Station Name"],
                            row["Station ID"],
                            row["GTFS Stop ID"],
                            row["Daytime Routes"],
                            row["Entrance Type"],
                            to_bool(row["Entry Allowed"]),
                            to_bool(row["Exit Allowed"]),
                            row["Entrance Latitude"],
                            row["Entrance Longitude"],
                        )
                    )

            # 4. Generate Spatial Points
            logger.info("Generating PostGIS Geometry points...")
            cur.execute("""
                UPDATE subway_entrances
                SET entrance_location = ST_SetSRID(
                        ST_MakePoint(entrance_longitude, entrance_latitude),
                        4326
                    );
            """)
            conn.commit()
            logger.info("Successfully loaded subway entrances!")


if __name__ == "__main__":
    load_entrances()
