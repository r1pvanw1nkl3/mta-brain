import pathlib
import time

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

import transit_core.core.models as md
from transit_core.config import get_settings

_SQL_DIR = pathlib.Path(__file__).resolve().parent.parent / "sql"


def _run_flyway(postgres: PostgresContainer, network: Network) -> None:
    """Apply the project's migrations with the real ``flyway/flyway`` image.

    Same tool and config as docker-compose/CI, run as a one-shot job on a
    shared network. Because it's real Flyway pointed at the real ``sql/``
    directory, new migration scripts and placeholders are picked up
    automatically -- the test schema can't silently drift from production.
    """
    flyway = (
        DockerContainer("flyway/flyway:latest-alpine")
        .with_network(network)
        .with_volume_mapping(str(_SQL_DIR), "/flyway/sql", "ro")
        .with_env("FLYWAY_URL", f"jdbc:postgresql://postgres:5432/{postgres.dbname}")
        .with_env("FLYWAY_USER", postgres.username)
        .with_env("FLYWAY_PASSWORD", postgres.password)
        .with_env("FLYWAY_PLACEHOLDERS_DB_NAME", postgres.dbname)
        .with_env("FLYWAY_PLACEHOLDERS_APP_USER", "app_user")
        .with_env("FLYWAY_PLACEHOLDERS_APP_PASSWORD", "app_password")
        .with_env("FLYWAY_LOCATIONS", "filesystem:/flyway/sql")
        .with_env("FLYWAY_CONNECT_RETRIES", "60")
        .with_command("-baselineOnMigrate=true -baselineVersion=0 migrate")
    )
    flyway.start()
    try:
        wrapped = flyway.get_wrapped_container()
        exit_code = wrapped.wait().get("StatusCode", 1)
        if exit_code != 0:
            logs = wrapped.logs().decode(errors="replace")
            raise RuntimeError(f"Flyway migration failed (exit {exit_code}):\n{logs}")
    finally:
        flyway.stop()


@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("DB_HOST", "test-host")
    monkeypatch.setenv("DB_PORT", "9999")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("ETL_DB_USER", "test_user")
    monkeypatch.setenv("ETL_DB_PASSWORD", "test_pass")
    monkeypatch.setenv("APP_DB_PASSWORD", "dummy")
    monkeypatch.setenv("APP_DB_USER", "test_user")

    get_settings.cache_clear()

    return get_settings()


@pytest.fixture(scope="module")
def redis_container():
    """Spins up a real Redis container for the duration of the test module."""
    with RedisContainer("redis:7.2-alpine") as redis:
        yield redis


@pytest.fixture(scope="module")
def postgres_container():
    """PostGIS (matching prod) with the project's real Flyway migrations applied.

    ``driver=None`` yields a plain ``postgresql://`` URL that psycopg3 accepts.
    Postgres and the Flyway job share a network so Flyway reaches it at the
    ``postgres`` alias, mirroring docker-compose.
    """
    with Network() as network:
        postgres = (
            PostgresContainer("postgis/postgis:16-3.4-alpine", driver=None)
            .with_network(network)
            .with_network_aliases("postgres")
        )
        with postgres:
            _run_flyway(postgres, network)
            yield postgres


@pytest.fixture
def feed_factory():
    """Returns a function that creates a valid Pydantic Feed model."""

    def _make_feed(trip_id="TRIP_1", stop_id="G08N", arrival_offset=300):
        arrival_ts = int(time.time()) + arrival_offset

        return md.Feed(
            header={"gtfs_realtime_version": "2.0", "timestamp": int(time.time())},
            entity=[
                md.Entity(
                    id="entity_1",
                    timestamp=str(int(time.time())),
                    trip_update=md.TripUpdate(
                        trip=md.Trip(
                            trip_id=trip_id, route_id="G", start_date=20260129
                        ),
                        stop_time_update=[
                            md.StopTimeUpdate(
                                stop_id=stop_id,
                                arrival=md.TimeUpdate(time=arrival_ts),
                            )
                        ],
                    ),
                )
            ],
        )

    return _make_feed
