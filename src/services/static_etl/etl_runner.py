import logging
import sys

from services.static_etl.gtfs_download import get_regular_feed, get_supplemented_feed
from services.static_etl.gtfs_parser import process_gtfs_zip
from transit_core.config import get_settings
from transit_core.db import create_db_pool, wait_for_db

logger = logging.getLogger(__name__)


def reload_all():
    run_reload(True)


def run_reload(all=False):
    settings = get_settings()

    logger.info("Downloading static GTFS feeds")
    if all:
        regular_file = get_regular_feed()
    supplemented_file = get_supplemented_feed()

    logger.info("Processing GTFS feeds and loading to DB")

    try:
        with create_db_pool(settings.etl_database_url) as pool:
            wait_for_db(pool)
            if all:
                logger.info("Loading regualr data")
                process_gtfs_zip(pool, regular_file, schema="public")
            logger.info("Loading supplemented data")
            process_gtfs_zip(pool, supplemented_file, schema="supplemented")
        logger.info("Full reload successful.")
    except Exception as e:
        logger.error(f"Reload failed: {e}")


if __name__ == "__main__":
    all = False
    if len(sys.argv) > 1:
        if sys.argv[1].upper() == "ALL":
            all = True
    run_reload(all)
