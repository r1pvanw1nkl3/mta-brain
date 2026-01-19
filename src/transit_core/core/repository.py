import logging
from typing import List

from transit_core.core.models import Station, StationSummary

logger = logging.getLogger(__name__)


class StationRepository:
    def __init__(self, db_pool):
        self.db = db_pool

    def get_station(self, stop_id: str) -> Station:
        sql_command = (
            "SELECT stop_id, stop_name, stop_lat, stop_lon, parent_station "
            "FROM stops WHERE stop_id = %s"
        )
        try:
            with self.db.connection() as conn:
                row = conn.execute(sql_command, (stop_id,)).fetchone()
        except Exception as e:
            logger.error(f"Failed to retrieve station: {e}")

        return Station(**row)

    def list_all_station_summaries(self) -> List[StationSummary]:
        sql_command = (
            "SELECT stop_id, stop_name FROM stops WHERE parent_station is null"
        )

        try:
            with self.db.connection() as conn:
                rows = conn.execute(sql_command).fetchall()

                return [StationSummary.model_validate(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get station summaries: {e}")
