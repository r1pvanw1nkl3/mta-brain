import logging
import time
from concurrent.futures import ThreadPoolExecutor

import services.subway_live_hydrator.feed_parser as fp
import services.subway_live_hydrator.state_manager as sm
import transit_core.redis_client as rc
from transit_core.config import get_settings
from transit_core.transit_core_logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

redis_client = rc.RedisClient(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    max_connections=settings.redis_max_connections,
)


def runner():
    urls = settings.gtfs_live_urls

    with ThreadPoolExecutor(max_workers=len(urls)) as executor:
        for key in urls:
            executor.submit(worker, key)

        while True:
            time.sleep(1)


def worker(key):
    urls = settings.gtfs_live_urls
    feed_url = urls[key]
    while True:
        try:
            start_time = time.time()

            raw_feed = fp.fetch_raw_feed(feed_url)
            if raw_feed is not None:
                if redis_client.is_feed_new(
                    key, int(raw_feed.get("header", {}).get("timestamp", 0))
                ):
                    feed = fp.validate_feed(raw_feed)
                    sm.update_redis_state(feed, redis_client)

            elapsed = time.time() - start_time
            sleep_time = max(0, (settings.redis_gtfs_ttl / 3) - elapsed)

            logger.info(f"Hydrated {feed_url} in {elapsed:.2f}s")
            time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Worker failed for {feed_url}: {e}")
            time.sleep(10)


if __name__ == "__main__":
    runner()
