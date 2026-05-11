from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient

from transit_core.api.routers import planner, stops, trips
from transit_core.config import get_settings
from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.repository import StopReader, TripReader
from transit_core.db import create_db_pool
from transit_core.infrastructure.census_gc_client import CensusGCClient
from transit_core.infrastructure.osrm_client import OsrmClient
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.infrastructure.static_store import PostgresStaticStore
from transit_core.redis_client import RedisClient
from transit_core.transit_core_logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_settings()

    redis_client = RedisClient(
        host=config.redis_host,
        port=config.redis_port,
        db=config.redis_db,
        max_connections=config.redis_max_connections,
    )

    app.state.state_store = RedisStateStore(redis_client)

    db_pool = create_db_pool(config.app_database_url)
    app.state.static_store = PostgresStaticStore(db_pool)

    async with AsyncClient() as http_client:
        geocoder = CensusGCClient(config.geocoding_service, http_client)

        app.state.stop_reader = StopReader(
            app.state.state_store, app.state.static_store, geocoder
        )
        app.state.trip_reader = TripReader(
            app.state.state_store, app.state.static_store
        )

        app.state.osrm_client = OsrmClient(config.osrm_url, http_client)
        app.state.planner_engine = PlannerEngine(
            app.state.stop_reader, app.state.osrm_client
        )
        yield

    db_pool.close()
    redis_client.client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(stops.router, prefix="/v1", tags=["Stops"])
app.include_router(trips.router, prefix="/v1", tags=["Trips"])
app.include_router(planner.router, prefix="/v1", tags=["Trip Planner"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
