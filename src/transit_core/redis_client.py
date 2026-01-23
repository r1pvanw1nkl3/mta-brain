import redis

from transit_core.core.models import TripUpdate

from .config import get_settings


class RedisState:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get_arrival_key(self, stop_id: str) -> str:
        return f"arrivals:{stop_id}"

    def get_trip_key(self, trip_id: str) -> str:
        return f"trip:{trip_id}"

    def update_live_state(self, trip_updates: list[TripUpdate], ttl: int = 90):
        with self.client.pipeline(transaction=False) as pipe:
            for trip in trip_updates:
                trip_key = self.get_trip_key(trip.trip_id)
                pipe.set(trip_key, trip.model_dump_json(), ex=ttl)

                for stop in trip.stops:
                    arrival_key = self.get_arrival_key(stop.stop_id)
                    pipe.zadd(arrival_key, {trip.trip_id: stop.arrival_time})
                    pipe.expire(arrival_key, ttl)


def get_redis_client():
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)
