import transit_core.config as cfg
import transit_core.core.repository as rp
import transit_core.db as db


def main():
    config = cfg.get_settings()
    with db.create_db_pool(config.app_database_url) as pool:
        repo = rp.StationRepository(pool)
        stations = repo.list_all_station_summaries()

        sorted_by_name = sorted(stations, key=lambda station: station.stop_name)

        for stop in sorted_by_name:
            print(stop.stop_name)


if __name__ == "__main__":
    main()
