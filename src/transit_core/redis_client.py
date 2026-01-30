from contextlib import contextmanager
from logging import getLogger

import redis

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
        logger.info("Creating redis connection pool")
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
        except Exception as e:
            logger.error(f"Redis pipeline execution failed: {e}")
            pipe.reset()
            raise e

    def get_header_timestamp_key(self, feed_url: str) -> str:
        return f"feed_timestamp:{feed_url}"

    def get_arrival_key(self, stop_id: str) -> str:
        return f"arrivals:{stop_id}"

    def get_trip_key(self, trip_id: str) -> str:
        return f"trip_state:{trip_id}"

    def is_feed_new(self, feed_url: str, new_timestamp: int) -> bool:
        key = self.get_header_timestamp_key(feed_url)
        last_ts = self.client.get(key)

        if last_ts and int(last_ts) >= new_timestamp:
            logger.info(
                f"""Feed {feed_url} is stale.
                Current ts: {new_timestamp}, cached: {last_ts}"""
            )
            return False

        logger.info(f"Feed {feed_url} is new. Updating cache with ts: {new_timestamp}")
        self.client.set(key, new_timestamp, ex=300)
        return True
