import time

import pytest
from testcontainers.redis import RedisContainer

import transit_core.core.models as md
from transit_core.config import get_settings


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
