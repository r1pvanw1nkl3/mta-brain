import sys
import time
from datetime import datetime

from transit_core.config import get_settings
from transit_core.core.repository import TripReader
from transit_core.db import create_db_pool
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.infrastructure.static_store import PostgresStaticStore
from transit_core.redis_client import RedisClient


def run_test(trip_id: str):
    config = get_settings()

    # 1. Setup Infrastructure
    redis_conn = RedisClient(
        host=config.redis_host, port=config.redis_port, db=config.redis_db
    )
    state_store = RedisStateStore(redis_conn)

    db_pool = create_db_pool(config.app_database_url)
    static_store = PostgresStaticStore(db_pool)

    # 2. Initialize Repository
    trip_repo = TripReader(state_store, static_store)

    # 3. Fetch Trip Arrivals
    print(f"\n--- Arrival Times for Trip: {trip_id} ---")
    print(f"Current Time: {datetime.now().strftime('%H:%M:%S')}\n")

    arrivals = trip_repo.get_trip_arrivals(trip_id)

    if not arrivals:
        print(f"No arrival data found for trip {trip_id} (Live or Static).")
        return

    # 4. Format Output
    print(f"{'STOP_ID':<10} | {'STOP_NAME':<30} | {'TIME':<8} | {'RELATIVE'}")
    print("-" * 70)

    # Sort arrivals by timestamp
    sorted_arrivals = sorted(arrivals.items(), key=lambda x: x[1])

    for stop_id, ts in sorted_arrivals:
        stop_name = static_store.get_stop_name(stop_id)

        arrival_dt = datetime.fromtimestamp(ts)
        clock_time = arrival_dt.strftime("%H:%M:%S")

        wait_time_seconds = ts - time.time()
        wait_minutes = round(wait_time_seconds / 60)

        if wait_minutes == 0:
            rel_str = "NOW"
        elif wait_minutes > 0:
            rel_str = f"in {wait_minutes}m"
        else:
            rel_str = f"{abs(wait_minutes)}m ago"

        print(f"{stop_id:<10} | {stop_name[:30]:<30} | {clock_time} | {rel_str}")


if __name__ == "__main__":
    # Default to a trip ID if none provided
    target_trip = sys.argv[1] if len(sys.argv) > 1 else "UNDEFINED"
    if target_trip == "UNDEFINED":
        print("Usage: python src/transit_core/scripts/test_trip_arrivals.py <id>")
    else:
        run_test(target_trip)
