import time

import transit_core.core.models as md
import transit_core.redis_client as rc
from transit_core.config import get_settings


def update_redis_state(feed: md.Feed, redis_client: rc.RedisClient):
    now = int(time.time())
    cfg = get_settings()

    pipe = redis_client.get_redis_pipeline()

    for entity in feed.entity:
        if entity.trip_update is not None:
            trip_id = entity.trip_update.trip.trip_id
            trip_data = entity.trip_update.model_dump_json()
            pipe.set(
                redis_client.get_trip_key(trip_id),
                trip_data,
                ex=cfg.redis_gtfs_ttl,
            )
            stop_time_update = entity.trip_update.stop_time_update
            if stop_time_update is not None:
                for stu in stop_time_update:
                    stop_id = stu.stop_id
                    arrival_key = redis_client.get_arrival_key(stop_id)
                    if stu.arrival_time:
                        arrival_time = stu.arrival_time.time
                    elif stu.departure_time:
                        arrival_time = stu.departure_time.time
                    else:
                        break
                pipe.zremrangebyscore(arrival_key, 0, now)
                pipe.zadd(arrival_key, {trip_id: arrival_time})
                pipe.expire(arrival_key, cfg.redis_gtfs_ttl)

    pipe.execute()
