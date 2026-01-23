import json
import time

import requests
from google.protobuf.json_format import MessageToDict

import transit_core.config as cfg
import transit_core.core.repository as rp
import transit_core.db as db
import transit_core.redis_client as rc
from transit_core.core.protos import gtfs_realtime_pb2


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


def download_raw_feed(filename="mta_dump.json"):
    url = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l"
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


if __name__ == "__main__":
    download_raw_feed()
