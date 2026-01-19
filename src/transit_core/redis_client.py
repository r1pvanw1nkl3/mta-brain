import redis

from .config import get_settings


def get_redis_client():
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)
