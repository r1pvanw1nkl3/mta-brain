import logging
import time

import transit_core.core.models as md
import transit_core.redis_client as rc
from transit_core.config import get_settings

logger = logging.getLogger(__name__)


def update_redis_state(feed: md.Feed, redis_client: rc.RedisClient):
    now = int(time.time())
    cfg = get_settings()

    trip_count = 0
    stop_update_count = 0
    start_time = time.time()

    with redis_client.pipeline_scope() as pipe:
        for entity in feed.entity:
            if entity.trip_update is not None:
                trip_count += 1
                trip_id = entity.trip_update.trip.trip_id
                trip_data = entity.trip_update.model_dump_json()
                logger.info(f"Adding trip ID to cache: {trip_id}")
                pipe.set(
                    redis_client.get_trip_key(trip_id),
                    trip_data,
                    ex=cfg.redis_gtfs_ttl,
                )
                stop_time_update = entity.trip_update.stop_time_update
                if stop_time_update is not None:
                    for stu in stop_time_update:
                        stop_update_count += 1
                        stop_id = stu.stop_id
                        arrival_key = redis_client.get_arrival_key(stop_id)
                        if stu.arrival_time:
                            arrival_time = stu.arrival_time.time
                        elif stu.departure_time:
                            arrival_time = stu.departure_time.time
                        else:
                            continue
                        logger.info(f"Adding trip {trip_id} to stop {stop_id}")
                        pipe.zremrangebyscore(arrival_key, 0, now)
                        pipe.zadd(arrival_key, {trip_id: arrival_time})
                        pipe.expire(arrival_key, cfg.redis_gtfs_ttl)

    logger.info(f"""Processed {trip_count} trips and {stop_update_count} stop updates
                in {time.time() - start_time:.4f}s""")
