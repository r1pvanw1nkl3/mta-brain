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
        today_fmt = now.strftime("%Y%m%d")

        start_time = (now - timedelta(minutes=30)).strftime("%H:%M:%S")
        end_time = (now + timedelta(minutes=lookahead_minutes)).strftime("%H:%M:%S")

        query = f"""
            WITH active_service AS (
                SELECT service_id FROM calendar
                WHERE {day_name} = 1
                  AND %s BETWEEN start_date AND end_date
                  AND service_id NOT IN (
                      SELECT service_id FROM calendar_dates
                      WHERE date = %s AND exception_type = 2
                  )
                UNION
                SELECT service_id FROM calendar_dates
                WHERE date = %s AND exception_type = 1
            )
            SELECT
                st.trip_id,
                st.arrival_time,
                t.route_id,
                t.trip_headsign,
                st.stop_id as platform_id,
                RIGHT(st.stop_id, 1) as direction
            FROM stop_times st
            JOIN trips t ON st.trip_id = t.trip_id
            JOIN active_service asvc ON t.service_id = asvc.service_id
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE (s.parent_station = %s OR s.stop_id = %s)
              AND st.arrival_time BETWEEN %s::interval AND %s::interval
            ORDER BY st.arrival_time ASC;
        """

        try:
            with self.pool.connection() as conn:
                results = conn.execute(
                    query,
                    (
                        today_fmt,
                        today_fmt,
                        today_fmt,
                        stop_id,
                        stop_id,
                        start_time,
                        end_time,
                    ),
                ).fetchall()
                return [self._format_row(row) for row in results]
        except Exception as e:
            logger.exception(
                "Failed to fetch scheduled arrivals",
                extra={"stop_id": stop_id, "error": str(e)},
            )

        return []

    def get_trip_metadata(self, trip_id: str) -> dict | None:
        query = """
            SELECT
                t.trip_id,
                t.route_id,
                t.trip_headsign,
                RIGHT(st.stop_id, 1) as direction
            FROM trips t
            LEFT JOIN stop_times st ON t.trip_id = st.trip_id
            WHERE t.trip_id LIKE %s
            LIMIT 1;
        """
        try:
            with self.pool.connection() as conn:
                # Use row_factory to get a dict if not already configured in pool
                row = conn.execute(query, (trip_id,)).fetchone()
                return row if row else None
        except Exception:
            logger.exception(
                "Failed to fetch trip metadata", extra={"trip_id": trip_id}
            )
            return None

    def get_stop_name(self, stop_id: str) -> str:
        # Handle platform IDs (e.g., A20N -> A20)
        base_stop_id = stop_id
        if len(stop_id) > 3 and stop_id[-1] in ("N", "S"):
            base_stop_id = stop_id[:-1]

        query = "SELECT stop_name FROM stops WHERE stop_id = %s LIMIT 1;"
        try:
            with self.pool.connection() as conn:
                row = conn.execute(query, (base_stop_id,)).fetchone()
                return row["stop_name"] if row else "Unknown"
        except Exception:
            return "Unknown"

    def get_trip_stop_times(self, trip_id: str) -> dict[str, int]:
        query = """
            SELECT stop_id, arrival_time
            FROM stop_times
            WHERE trip_id = %s
            ORDER BY stop_sequence;
        """
        try:
            with self.pool.connection() as conn:
                results = conn.execute(query, (trip_id,)).fetchall()
                if not results:
                    # Suffix match fallback
                    query_suffix = """
                        SELECT stop_id, arrival_time
                        FROM stop_times
                        WHERE trip_id LIKE %s
                        ORDER BY stop_sequence;
                    """
                    results = conn.execute(query_suffix, ("%" + trip_id,)).fetchall()

                return {
                    row["stop_id"]: self._to_epoch(row["arrival_time"])
                    for row in results
                }
        except Exception:
            logger.exception(
                "Failed to fetch trip stop times", extra={"trip_id": trip_id}
            )
            return {}

    def get_stop_names(self, stop_ids: list[str]) -> dict[str, str]:
        query = "select stop_id, stop_name FROM stops WHERE stop_id = ANY(%s)"
        with self.pool.connection() as conn:
            rows = conn.execute(query, (stop_ids,))
        return {row["stop_id"]: row["stop_name"] for row in rows}

    def _format_row(self, row: dict) -> dict:
        row["arrival_timestamp"] = self._to_epoch(row["arrival_time"])
        row["arrival_time_str"] = str(row["arrival_time"])
        return row

    def _to_epoch(self, arrival_delta: timedelta) -> int:
        service_day = datetime.combine(date.today(), datetime.min.time())
        return int((service_day + arrival_delta).timestamp())
