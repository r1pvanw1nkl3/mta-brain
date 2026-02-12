import time

import pytest

import transit_core.redis_client as rc
from services.subway_live_hydrator.state_manager import hydrate_realtime_data
from transit_core.config import get_settings
from transit_core.core.repository import Keys, StopWriter, TripWriter
from transit_core.infrastructure.state_store import RedisStateStore


@pytest.mark.filterwarnings("ignore:wait_container_is_ready")
def test_redis_integration_lifecycle(redis_container, feed_factory):
    # Setup connection
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    redis_client = rc.RedisClient(host=host, port=port, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)
    trip_repo = TripWriter(state_store=state_store)
    stop_repo = StopWriter(state_store=state_store)

    # 1. Use the factory to create REAL data
    trip_id = "REAL_TRIP_123"
    stop_id = "G08N"

    real_feed = feed_factory(trip_id=trip_id, stop_id=stop_id, arrival_offset=600)

    # 2. Run the hydration
    hydrate_realtime_data(feed=real_feed, trip_repo=trip_repo, stop_repo=stop_repo)

    # 3. Assertions via Repositories

    # Check Trip Status
    trip_status = trip_repo.get_trip_status(trip_id)
    assert trip_status is not None
    assert trip_status.trip.trip_id == trip_id

    # 4. Verify Raw Key Mappings and TTL
    cfg = get_settings()

    # Trip key
    trip_key = Keys.trip(trip_id)
    assert redis_client.client.exists(trip_key)
    ttl = redis_client.client.ttl(trip_key)
    assert 0 < ttl <= cfg.trip_metadata_ttl

    # Departures key
    arrivals_key = Keys.arrivals(stop_id)
    assert redis_client.client.exists(arrivals_key)
    ttl = redis_client.client.ttl(arrivals_key)
    assert 0 < ttl <= cfg.redis_gtfs_ttl


@pytest.mark.filterwarnings("ignore:wait_container_is_ready")
def test_feed_deduplication(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis_client = rc.RedisClient(host=host, port=port, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)

    feed_key = Keys.feed("G")
    ts = 1700000000

    # First time - should succeed
    assert state_store.check_and_update_timestamp(feed_key, ts) is True
    assert int(redis_client.client.get(feed_key)) == ts

    # Second time with same timestamp - should fail
    assert state_store.check_and_update_timestamp(feed_key, ts) is False

    # Third time with older timestamp - should fail
    assert state_store.check_and_update_timestamp(feed_key, ts - 1) is False

    # Fourth time with newer timestamp - should succeed
    assert state_store.check_and_update_timestamp(feed_key, ts + 1) is True
    assert int(redis_client.client.get(feed_key)) == ts + 1


@pytest.mark.filterwarnings("ignore:wait_container_is_ready")
def test_multiple_concurrent_feeds(redis_container, feed_factory):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis_client = rc.RedisClient(host=host, port=port, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)
    trip_repo = TripWriter(state_store=state_store)
    stop_repo = StopWriter(state_store=state_store)

    # Feed 1: Trip A at Stop S
    feed1 = feed_factory(trip_id="TRIP_A", stop_id="STOP_S", arrival_offset=600)
    # Feed 2: Trip B at Stop S
    feed2 = feed_factory(trip_id="TRIP_B", stop_id="STOP_S", arrival_offset=900)

    hydrate_realtime_data(feed1, trip_repo, stop_repo)
    hydrate_realtime_data(feed2, trip_repo, stop_repo)

    # Both should be present on the same board
    arrivals = state_store.get_zset(Keys.arrivals("STOP_S"))
    assert "TRIP_A" in arrivals
    assert "TRIP_B" in arrivals
    assert arrivals["TRIP_A"] > time.time()
    assert arrivals["TRIP_B"] > arrivals["TRIP_A"]


@pytest.mark.filterwarnings("ignore:wait_container_is_ready")
def test_ttl_expiration(redis_container, feed_factory):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis_client = rc.RedisClient(host=host, port=port, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)
    trip_repo = TripWriter(state_store=state_store)
    stop_repo = StopWriter(state_store=state_store)

    stop_id = "TTL_STOP"
    feed = feed_factory(trip_id="TTL_TRIP", stop_id=stop_id, arrival_offset=600)

    # Set a very short TTL for testing
    # Since we can't easily change settings globally here without affecting others
    # we can just manually set a short TTL if we wanted to test expiration
    # but for integration tests, we usually just verify it *has* a TTL.
    hydrate_realtime_data(feed, trip_repo, stop_repo)

    arrivals_key = Keys.arrivals(stop_id)
    redis_client.client.expire(arrivals_key, 1)  # 1 second

    assert redis_client.client.exists(arrivals_key)
    time.sleep(1.1)
    assert not redis_client.client.exists(arrivals_key)
