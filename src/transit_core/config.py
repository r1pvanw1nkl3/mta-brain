# transit_core/config.py

from functools import lru_cache
from pathlib import Path

from psycopg.conninfo import make_conninfo
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "mta_brain"

    etl_db_user: str
    etl_db_password: str

    app_db_user: str
    app_db_password: str

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_max_connections: int = 20
    redis_gtfs_ttl: int = 45

    gtfs_static_url: str = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
    gtfs_supplemented_url: str = (
        "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_supplemented.zip"
    )

    gtfs_live_urls: list[str] = [
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
    ]

    gtfs_realtime_retries: int = 3
    gtfs_timeout: int = 5
    gtfs_retry_delay: int = 2

    project_root: str = str(Path(__file__).resolve().parent.parent.parent)
    log_file_path: str = "logs/app.log"
    etl_log_file_path: str = "logs/etl.log"
    gtfs_static_path: str = "gtfs_static"

    @computed_field
    def etl_database_url(self) -> str:
        return make_conninfo(
            host=self.db_host,
            port=str(self.db_port),
            dbname=self.db_name,
            user=self.etl_db_user,
            password=self.etl_db_password,
        )

    @computed_field
    def app_database_url(self) -> str:
        return make_conninfo(
            host=self.db_host,
            port=str(self.db_port),
            dbname=self.db_name,
            user=self.app_db_user,
            password=self.app_db_password,
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache()
def get_settings():
    return Settings()
