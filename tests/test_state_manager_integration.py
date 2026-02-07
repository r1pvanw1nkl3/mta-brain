import pytest

import transit_core.redis_client as rc
from services.subway_live_hydrator.state_manager import hydrate_realtime_data
from transit_core.config import get_settings
from transit_core.core.repository import Keys, StopRepository, TripRepository
from transit_core.infrastructure.state_store import RedisStateStore


@pytest.mark.filterwarnings("ignore:wait_container_is_ready")
def test_redis_integration_lifecycle(redis_container, feed_factory):
    # Setup connection
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    redis_client = rc.RedisClient(host=host, port=port, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)
    trip_repo = TripRepository(state_store=state_store)
    stop_repo = StopRepository(state_store=state_store)

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

    # 4. Verify Raw Key Mappings and TTL (Optional but good for integration)
    cfg = get_settings()

    # Trip key
    trip_key = Keys.trip(trip_id)
    assert redis_client.client.exists(trip_key)
    ttl = redis_client.client.ttl(trip_key)
    assert 0 < ttl <= cfg.redis_gtfs_ttl

    # Departures key
    arrivals_key = Keys.arrivals(stop_id)
    assert redis_client.client.exists(arrivals_key)
    ttl = redis_client.client.ttl(arrivals_key)
    assert 0 < ttl <= cfg.redis_gtfs_ttl
