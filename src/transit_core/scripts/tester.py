import time

import transit_core.config as cfg
import transit_core.core.repository as rp
import transit_core.db as db
import transit_core.redis_client as rc


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


if __name__ == "__main__":
    main()
