import json
import time

import requests
from google.protobuf.json_format import MessageToDict

import services.subway_live_hydrator.feed_parser as fp
import services.subway_live_hydrator.runner as runner
import services.subway_live_hydrator.state_manager as sm
import transit_core.config as cfg
import transit_core.core.repository as rp
import transit_core.db as db
import transit_core.redis_client as rc
from transit_core.core.protos import gtfs_realtime_pb2
from transit_core.transit_core_logging import setup_logging

setup_logging()


def main():
    config = cfg.get_settings()
    with db.create_db_pool(config.app_database_url) as pool:
        repo = rp.StationRepository(pool)
        stations = repo.list_all_station_summaries()

        sorted_by_name = sorted(stations, key=lambda station: station.stop_name)

        for stop in sorted_by_name:
            print(stop.stop_name)


def redis_test():
    with rc.get_redis_client() as r:
        r.set("test", "abbadabba", 5)
        print(r.ttl("test"))
        print(r.get("test"))
        time.sleep(5)
        print(r.get("test"))


def download_raw_feed(url, filename="mta_dump.json"):
    try:
        # Fetching the data
        response = requests.get(url)
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()

        feed.ParseFromString(response.content)

        feed_dict = MessageToDict(feed, preserving_proto_field_name=True)

        # 4. Save the dictionary as JSON
        with open(filename, "w") as f:
            json.dump(feed_dict, f, indent=4)

        print(f"Data successfully dumped to {filename}")

    except Exception as e:
        print(f"Error fetching data: {e}")


def gtfs_load_test():
    settings = cfg.get_settings()
    feed = settings.gtfs_live_urls[7]
    fp.fetch_raw_feed(feed)
    # feed = fp.validate_feed(raw_feed)
    # with open("model_dump.json", "w") as file:
    #     file.write(feed.model_dump_json(indent=4))


def gtfs_to_redis_test():
    settings = cfg.get_settings()
    redis_client = rc.RedisClient(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        max_connections=settings.redis_max_connections,
    )

    feed_url = settings.gtfs_live_urls[7]
    feed = fp.fetch_raw_feed(feed_url)
    sm.update_redis_state(feed=feed, redis_client=redis_client)


def test_runner():
    runner.runner()


if __name__ == "__main__":
    test_runner()
