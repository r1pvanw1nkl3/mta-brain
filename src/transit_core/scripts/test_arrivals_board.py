import time
from datetime import datetime

from transit_core.config import get_settings
from transit_core.core.repository import StopReader
from transit_core.db import create_db_pool
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.infrastructure.static_store import PostgresStaticStore
from transit_core.redis_client import RedisClient


def run_test():
    config = get_settings()
    # 1. Setup Infrastructure
    redis_conn = RedisClient(
        host=config.redis_host, port=config.redis_port, db=config.redis_db
    )
    state_store = RedisStateStore(redis_conn)

    db_pool = create_db_pool(config.app_database_url)
    static_store = PostgresStaticStore(db_pool)

    # 2. Initialize Repository
    stop_repo = StopReader(state_store, static_store)

    # 3. Fetch Unified Board for 86th St (A21)
    # Note: Use 'A21' for 86th St Central Park West (A/B/C)
    stop_id = "635"
    print(f"\n--- Unified Departure Board for {stop_id} ---")
    print(f"Current Time: {datetime.now().strftime('%H:%M:%S')}\n")

    board = stop_repo.get_arrivals_board(stop_id, 240)

    # 4. Format Output
    print(f"{'ROUTE':<6} | {'DESTINATION':<25} | {'TIME':<8} | {'STATUS':<12}")
    print("-" * 60)

    for train in board:
        # Now actually using the arrival_dt for the clock time
        arrival_dt = datetime.fromtimestamp(train.arrival_time)
        clock_time = arrival_dt.strftime("%H:%M")

        wait_time_seconds = train.arrival_time - time.time()
        wait_minutes = round(wait_time_seconds / 60)

        # Skip trains that have already passed
        if wait_minutes < -1:
            continue

        wait_str = f"{wait_minutes}m" if wait_minutes > 0 else "NOW"

        departure_string = (
            f"{train.route_id:<6} | {train.headsign[:25]:<25}"
            f"| {clock_time} ({wait_str:<4}) | {train.status:<12}"
        )
        # Added the clock_time to the print output
        print(departure_string)


if __name__ == "__main__":
    run_test()
