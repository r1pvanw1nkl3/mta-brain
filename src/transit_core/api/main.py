from contextlib import asynccontextmanager

from fastapi import FastAPI

from transit_core.api.routers import stops, trips
from transit_core.config import get_settings
from transit_core.db import create_db_pool
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.infrastructure.static_store import PostgresStaticStore
from transit_core.redis_client import RedisClient


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
    yield

    db_pool.close()
    redis_client.client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(stops.router)
app.include_router(trips.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
