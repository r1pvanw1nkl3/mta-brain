import logging
import time
from concurrent.futures import ThreadPoolExecutor

import services.subway_live_hydrator.feed_parser as fp
import services.subway_live_hydrator.state_manager as sm
import transit_core.redis_client as rc
from transit_core.config import get_settings
from transit_core.core.protos import gtfs_realtime_pb2, nyct_subway_pb2  # noqa: F401
from transit_core.core.repository import Keys, StopWriter, TripWriter
from transit_core.infrastructure.state_store import RedisStateStore
from transit_core.transit_core_logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


settings = get_settings()


def runner():
    redis_client = rc.RedisClient(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        max_connections=settings.redis_max_connections,
    )

    state_store = RedisStateStore(redis_client=redis_client)
    trip_repo = TripWriter(state_store=state_store)
    stop_repo = StopWriter(state_store=state_store)

    urls = settings.gtfs_live_urls
    logger.info(f"Starting runner for the following feeds: {' '.join(urls.keys())}")
    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        for key in urls:
            executor.submit(worker, key, trip_repo, stop_repo, state_store)

        while True:
            time.sleep(1)


def worker(key, trip_repo, stop_repo, state_store):
    urls = settings.gtfs_live_urls
    feed_url = urls[key]
    from transit_core.core.exceptions import FeedError, StorageError

    while True:
        try:
            start_time = time.time()

            raw_feed = fp.fetch_raw_feed(feed_url)
            if raw_feed is not None:
                if state_store.check_and_update_timestamp(
                    Keys.feed(key), int(raw_feed.get("header", {}).get("timestamp", 0))
                ):
                    feed = fp.validate_feed(raw_feed)
                    sm.hydrate_realtime_data(
                        feed=feed, trip_repo=trip_repo, stop_repo=stop_repo
                    )

            elapsed = time.time() - start_time
            sleep_time = max(0, (settings.redis_gtfs_ttl / 3) - elapsed)

            logger.info(
                "Hydrated feed",
                extra={
                    "feed_key": key,
                    "feed_url": feed_url,
                    "elapsed_seconds": round(elapsed, 2),
                },
            )
            time.sleep(sleep_time)

        except (FeedError, StorageError) as e:
            logger.error(
                "Known error during worker execution",
                extra={
                    "feed_url": feed_url,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            time.sleep(10)
        except Exception:
            logger.exception("Unexpected worker failure", extra={"feed_url": feed_url})
            time.sleep(10)


if __name__ == "__main__":
    runner()
