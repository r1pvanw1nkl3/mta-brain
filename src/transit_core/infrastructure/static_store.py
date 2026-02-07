from datetime import date, datetime, timedelta
from logging import getLogger

from psycopg_pool import ConnectionPool

logger = getLogger(__name__)


class PostgresStaticStore:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def get_scheduled_arrivals(self, stop_id: str, lookahead_minutes) -> list[dict]:
        now = datetime.now()
        day_name = now.strftime("%A").lower()

        start_time = (now - timedelta(minutes=5)).strftime("%H:%M:%S")
        end_time = (now + timedelta(minutes=lookahead_minutes)).strftime("%H:%M:%S")

        query = f"""
            SELECT
                st.trip_id,
                st.arrival_time,
                t.route_id,
                t.trip_headsign,
                st.stop_id as platform_id,
                RIGHT(st.stop_id, 1) as direction
            FROM stop_times st
            JOIN trips t ON st.trip_id = t.trip_id
            JOIN calendar c ON t.service_id = c.service_id
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE (s.parent_station = %s OR s.stop_id = %s)
              AND c.{day_name} = 1
              AND TO_CHAR(CURRENT_DATE, 'YYYYMMDD') BETWEEN c.start_date AND c.end_date
              AND st.arrival_time BETWEEN %s::interval AND %s::interval
            ORDER BY st.arrival_time ASC;
        """

        try:
            with self.pool.connection() as conn:
                results = conn.execute(
                    query, (stop_id, stop_id, start_time, end_time)
                ).fetchall()
                return [self._format_row(row) for row in results]
        except Exception as e:
            logger.exception(
                "Failed to fetch scheduled arrivals",
                extra={"stop_id": stop_id, "error": str(e)},
            )

        return []

    def get_trip_metadata(self, trip_id: str) -> dict | None:
        return

    def _format_row(self, row: dict) -> dict:
        row["arrival_timestamp"] = self._to_epoch(row["arrival_time"])
        row["arrival_time_str"] = str(row["arrival_time"])
        return row

    def _to_epoch(self, arrival_delta: timedelta) -> int:
        service_day = datetime.combine(date.today(), datetime.min.time())
        return int((service_day + arrival_delta).timestamp())
