import asyncio

from httpx import AsyncClient

from transit_core.config import get_settings
from transit_core.core.repository import StopReader
from transit_core.db import create_db_pool
from transit_core.infrastructure.census_gc_client import CensusGCClient
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.infrastructure.static_store import PostgresStaticStore
from transit_core.messenger.adapters.command_line import CommandLineAdapter
from transit_core.messenger.handler import Handler
from transit_core.redis_client import RedisClient
from transit_core.transit_core_logging import setup_logging


async def _run():
    setup_logging()
    config = get_settings()

    redis_client = RedisClient(
        host=config.redis_host,
        port=config.redis_port,
        db=config.redis_db,
        max_connections=config.redis_max_connections,
    )
    db_pool = create_db_pool(config.app_database_url)

    state_store = RedisStateStore(redis_client)
    static_store = PostgresStaticStore(db_pool)

    try:
        async with AsyncClient() as http_client:
            geocoder = CensusGCClient(config.geocoding_service, http_client)
            stop_reader = StopReader(state_store, static_store, geocoder)

            handler = Handler(stop_reader=stop_reader)
            adapters = [CommandLineAdapter(handler)]

            await asyncio.gather(*(a.start() for a in adapters))
    finally:
        db_pool.close()
        redis_client.client.close()


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
