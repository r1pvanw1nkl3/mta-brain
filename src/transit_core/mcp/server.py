import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP

from transit_core.config import get_settings
from transit_core.core.repository import StopReader, TripReader
from transit_core.db import create_db_pool
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.infrastructure.static_store import PostgresStaticStore
from transit_core.redis_client import RedisClient
from transit_core.transit_core_logging import setup_logging

setup_logging()

logger = logging.getLogger(__name__)
config = get_settings()


@asynccontextmanager
async def lifespan(server: FastMCP):
    logger.info("initializing resources...")

    redis_client = RedisClient(
        host=config.redis_host,
        port=config.redis_port,
        db=config.redis_db,
        max_connections=config.redis_max_connections,
    )

    db_pool = create_db_pool(config.app_database_url)

    state_store = RedisStateStore(redis_client)
    static_store = PostgresStaticStore(db_pool)

    readers = {
        "stop_reader": StopReader(state_store, static_store),
        "trip_reader": TripReader(state_store, static_store),
    }

    yield readers

    logger.info("Deallocating resources")
    db_pool.close()
    redis_client.client.close()


mcp = FastMCP("MTA-Brain", lifespan=lifespan)


@mcp.tool()
def get_station_info(stop_id: str, ctx: Context) -> list[dict]:
    """
    Fetch live and scheduled arrival times for a specific NYC subway stop.

    Use this tool when you need to know what trains are ariving at a stop,
    their destinations, and how many minutes away they are.

    :param stop_id: The GTFS Stop ID. Use the base ID (e.g., 'A20') for all arrivals,
                    or append 'N' or 'S' (e.g., 'A20N') for specific directions.
    :return: A list of upcoming train arrivals with routes and destinations.
    """
    logger.info(f"Tool get_station_info called with stop_id: {stop_id}")

    try:
        # lifespan_context is stored in request_context
        reader = ctx.request_context.lifespan_context["stop_reader"]
        logger.debug("Running repository call...")
        arrivals = reader.get_arrivals_board(stop_id)
        logger.debug(f"Repository call returned {len(arrivals)} arrivals")

        now = int(time.time())
        results = []
        for a in arrivals:
            minutes_away = max(0, (a.arrival_time - now) // 60)
            clock_time = (
                datetime.fromtimestamp(a.arrival_time).strftime("%I:%M %p").lstrip("0")
            )
            results.append(
                {
                    "route": a.route_id,
                    "destination": a.headsign,
                    "minutes_away": minutes_away,
                    "clock_time": clock_time,
                    "status": a.status,
                    "trip_id": a.trip_id,
                }
            )

        return results
    except Exception as e:
        logger.exception(f"Error in get_station_info: {e}")
        raise


@mcp.tool()
def get_trip_arrivals(trip_id: str, ctx: Context) -> list[dict]:
    """
    Fetch all upcoming stop arrivals for a specific trip (train).

    Use this tool when you know a trip ID and want to see its full schedule
    or live progress through the stations.

    :param trip_id: The GTFS Trip ID.
    :return: A list of stops and arrival times for the trip.
    """
    logger.info(f"Tool get_trip_arrivals called with trip_id: {trip_id}")
    try:
        reader = ctx.request_context.lifespan_context["trip_reader"]
        arrivals = reader.get_trip_arrivals(trip_id)

        now = int(time.time())
        results = []
        for a in arrivals:
            ts = a["arrival_time"]
            if ts:
                minutes_away = (ts - now) // 60
                clock_time = datetime.fromtimestamp(ts).strftime("%I:%M %p").lstrip("0")
                time_str = f"{minutes_away}m ({clock_time})"
            else:
                minutes_away = None
                clock_time = None
                time_str = "N/A"

            results.append(
                {
                    "stop_id": a["stop_id"],
                    "stop_name": a["stop_name"],
                    "minutes_away": minutes_away,
                    "clock_time": clock_time,
                    "time_display": time_str,
                }
            )

        return results
    except Exception as e:
        logger.exception(f"Error in get_trip_arrivals: {e}")
        raise


@mcp.tool()
def station_search(search_string: str, ctx: Context) -> list[dict]:
    """
    Perform a search for a user

    :param search_string: Description
    :type search_string: str
    :param ctx: Description
    :type ctx: Context
    :return: Description
    :rtype: list[dict]
    """


# At the bottom of server.py
if __name__ == "__main__":
    mcp.run()
