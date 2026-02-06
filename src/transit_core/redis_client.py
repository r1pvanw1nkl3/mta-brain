from contextlib import contextmanager
from logging import getLogger

import redis

from transit_core.core.exceptions import CacheError

logger = getLogger(__name__)


class RedisClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        max_connections: int = 20,
        decode_responses: bool = True,
    ):
        logger.info(
            "Creating redis connection pool",
            extra={"host": host, "port": port, "db": db},
        )
        self._pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses,
            max_connections=max_connections,
        )
        self.client = redis.Redis(connection_pool=self._pool)

    @contextmanager
    def pipeline_scope(self):
        pipe = self.client.pipeline()
        try:
            yield pipe
            pipe.execute()
        except redis.RedisError as e:
            logger.exception("Redis pipeline execution failed")
            pipe.reset()
            raise CacheError(f"Redis pipeline failed: {e}") from e
        except Exception:
            logger.exception("Unexpected error during Redis pipeline execution")
            pipe.reset()
            raise
