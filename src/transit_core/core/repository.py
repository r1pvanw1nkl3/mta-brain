import logging
import time
from typing import List

from transit_core.core.models import Station, StationSummary

logger = logging.getLogger(__name__)


class StationRepository:
    def __init__(self, db_pool):
        self.db = db_pool

    def get_station(self, stop_id: str) -> Station:
        logger.debug(f"Fetching station details for stop_id: {stop_id}")
        start_time = time.time()
        sql_command = (
            "SELECT stop_id, stop_name, stop_lat, stop_lon, parent_station "
            "FROM stops WHERE stop_id = %s"
        )
        try:
            with self.db.connection() as conn:
                row = conn.execute(sql_command, (stop_id,)).fetchone()
            logger.info(
                f"get_station query executed in {time.time() - start_time:.4f}s"
            )
        except Exception as e:
            logger.error(f"Failed to retrieve station: {e}")

        return Station(**row)

    def list_all_station_summaries(self) -> List[StationSummary]:
        start_time = time.time()
        sql_command = (
            "SELECT stop_id, stop_name FROM stops WHERE parent_station is null"
        )

        try:
            with self.db.connection() as conn:
                rows = conn.execute(sql_command).fetchall()

                summaries = [StationSummary.model_validate(row) for row in rows]
                logger.info(f"""Fetched {len(summaries)} station summaries
                            in {time.time() - start_time:.4f}s""")
                return summaries

        except Exception as e:
            logger.error(f"Failed to get station summaries: {e}")
