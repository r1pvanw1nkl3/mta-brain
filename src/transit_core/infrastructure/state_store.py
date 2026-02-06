import logging
import threading
from contextlib import contextmanager
from typing import Dict, Union

from transit_core.redis_client import RedisClient

logger = logging.getLogger(__name__)

RedisScore = Union[int, float]
Mapping = Dict[str, RedisScore]


class RedisStateStore:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self._local = threading.local()

    @property
    def _active_pipe(self):
        return getattr(self._local, "pipe", None)

    @_active_pipe.setter
    def _active_pipe(self, value):
        self._local.pipe = value

    @contextmanager
    def batch_session(self):
        with self.redis.pipeline_scope() as pipe:
            self._active_pipe = pipe
            try:
                yield
            finally:
                self._active_pipe = None

    def _get_client(self):
        return self._active_pipe or self.redis.client

    def set_kv(self, key: str, value: str, expiry) -> None:
        self._get_client().set(key, value, ex=expiry)

    def get_kv(self, key: str) -> str | None:
        return self.redis.client.get(key)

    def sync_set(self, key: str, mapping: Mapping, min_score: int, expiry) -> None:
        self._get_client().zremrangebyscore(key, 0, min_score)
        if mapping:
            self._get_client().zadd(key, mapping)
            self._get_client().expire(key, expiry)

    def get_zset(self, key: str) -> dict[str, int]:
        raw_data = self.redis.client.zrange(key, 0, -1, withscores=True)
        return {member: int(score) for member, score in raw_data}

    def check_and_update_timestamp(self, key: str, timestamp: int) -> bool:
        client = self.redis.client
        last_ts_raw = client.get(key)
        try:
            last_ts = int(last_ts_raw) if last_ts_raw else 0
        except (ValueError, TypeError):
            last_ts = 0

        if last_ts >= timestamp:
            return False
        else:
            client.set(key, timestamp)
            return True
