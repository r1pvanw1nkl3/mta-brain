import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastmcp import Context, FastMCP

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


mcp = FastMCP(
    "MTA-Brain",
    lifespan=lifespan,
    instructions="""
                You are 'NYC Transit Brain,' an authentic, adaptive AI collaborator.
                Your goal is to help users navigate
                the NYC subway system with empathy and candor.

                OPERATIONAL PROTOCOLS:
                1. Mandatory Resolution:
                If a user provides a station name, you MUST call 'station_search' first.
                Never guess a GTFS Stop ID.
                2. Data Privacy:
                NEVER expose internal IDs (Stop IDs like 'A20' or Trip IDs) to the user.
                Always use human-friendly station names and route letters.
                3. Disambiguation:
                For stations with multiple matches (e.g., '23 St'),
                use the 'routes' field to help the user choose the correct one
                (e.g., 'The 23rd St on the F/M lines').
                4. Conversational Style:
                Be helpful and grounded. If service is delayed, be direct but supportive
              """,
)


@mcp.tool()
def get_station_info(stop_id: str, ctx: Context) -> list[dict] | None:
    """
    Fetch live and scheduled arrival times for a stop using a specific GTFS ID.

    Use this tool ONLY when you have a valid GTFS Stop ID (e.g., 'L06', 'A20').
    If you only have a station name, you must call 'station_search' first
    to resolve it to an ID.

    :param stop_id: The internal GTFS Stop ID. Use the parent ID for all
                    arrivals at that station.
    :return: A list of upcoming train arrivals with routes, destinations,
            and minutes until arrival.
    """
    logger.info(f"Tool get_station_info called with stop_id: {stop_id}")

    if ctx.request_context is None:
        logger.error("station_search called without a request context")
        return None

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
def get_trip_arrivals(trip_id: str, ctx: Context) -> list[dict] | None:
    """
    Fetch all upcoming stop arrivals for a specific trip (train).

    Use this tool when you know a trip ID and want to see its full schedule
    or live progress through the stations.

    :param trip_id: The GTFS Trip ID.
    :return: A list of stops and arrival times for the trip.
    """
    logger.info(f"Tool get_trip_arrivals called with trip_id: {trip_id}")

    if ctx.request_context is None:
        logger.error("station_search called without a request context")
        return None

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
def station_search(search_string: str, ctx: Context) -> list[dict] | None:
    """
    Find the GTFS Stop ID for an NYC subway station using its common name.

    Use this tool FIRST whenever a user mentions a station name (e.g., "Bedford Av",
    "23rd St", "Atlantic Av"). You MUST use this tool to obtain the correct
    'stop_id' before calling get_station_info.

    Since many NYC stations share names (like '23 St'), this tool returns
    multiple ranked results. Use the 'routes' field in the results to
    disambiguate which station the user is likely looking for.

    :param search_string: The station name or approximate name provided by the user.
    :return: List of matches including 'stop_id' (internal GTFS stop ID),
    'stop_name', 'routes' (lines served), and 'rank'.
    Use the 'routes' to help the user select a station.
    DO NOT show the stop_id to the user.
    """

    if ctx.request_context is None:
        logger.error("station_search called without a request context")
        return None

    logger.info(f"Tool station_search called with search string: {search_string}")
    try:
        reader = ctx.request_context.lifespan_context["stop_reader"]
        return reader.fuzzy_station_search(search_string)
    except Exception as e:
        logger.exception(f"Error in station_search: {e}")


# At the bottom of server.py
if __name__ == "__main__":
    mcp.run()
