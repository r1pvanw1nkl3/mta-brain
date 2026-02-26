import logging
import sys
import time
from typing import LiteralString

from services.static_etl.gtfs_download import get_regular_feed, get_supplemented_feed
from services.static_etl.gtfs_parser import process_gtfs_zip
from transit_core.config import get_settings
from transit_core.db import create_db_pool, wait_for_db
from transit_core.transit_core_logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def reload_all():
    run_reload(True)


def run_reload(all=False):
    settings = get_settings()
    logger.info("Starting ETL reload", extra={"all_feeds": all})

    logger.info("Downloading static GTFS feeds")
    start_download = time.time()
    try:
        if all:
            regular_file = get_regular_feed()
        supplemented_file = get_supplemented_feed()
    except Exception:
        logger.exception("Failed to download GTFS feeds")
        return

    logger.info(
        "Download phase completed",
        extra={"elapsed_seconds": round(time.time() - start_download, 2)},
    )

    logger.info("Processing GTFS feeds and loading to DB")
    start_process = time.time()

    try:
        with create_db_pool(settings.etl_database_url) as pool:
            wait_for_db(pool)
            if all:
                logger.info("Loading regular data")
                process_gtfs_zip(pool, regular_file, schema="public")
            logger.info("Loading supplemented data")
            process_gtfs_zip(pool, supplemented_file, schema="supplemented")
            logger.info("refreshing view...")

            query: LiteralString = "REFRESH MATERIALIZED VIEW  mv_station_services"
            with pool.connection() as conn:
                conn.execute(query)
        logger.info(
            "Full reload successful, view refreshed",
            extra={"elapsed_seconds": round(time.time() - start_process, 2)},
        )

    except Exception:
        logger.exception("Reload failed")


if __name__ == "__main__":
    all = False
    if len(sys.argv) > 1:
        if sys.argv[1].upper() == "ALL":
            logger.info("Performing full refresh.")
            all = True
        else:
            logger.info("Performing supplemented refresh.")
    run_reload(all)
