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

    redis_url: str = "redis://localhost:6379/0"

    gtfs_static_url: str = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
    gtfs_supplemented_url: str = (
        "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_supplemented.zip"
    )

    gtfs_live_urls: dict[str, str] = {
        "ace": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
        "bdfm": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
        "g": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
        "jz": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
        "nqrw": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
        "l": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
        "123": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
        "7": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-7",
        "sir": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si",
    }

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
