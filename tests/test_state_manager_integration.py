# tests/test_state_manager_integration.py
import time

import pytest

from services.subway_live_hydrator.state_manager import update_redis_state
from transit_core.redis_client import RedisClient


@pytest.mark.filterwarnings("ignore:wait_container_is_ready")
def test_redis_integration_lifecycle(redis_container, feed_factory):
    # Setup connection
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = RedisClient(host=host, port=port, decode_responses=True)

    # 1. Use the factory to create REAL data
    trip_id = "REAL_TRIP_123"
    stop_id = "G08N"
    arrival_ts = int(time.time()) + 600

    real_feed = feed_factory(trip_id=trip_id, stop_id=stop_id, arrival_offset=600)

    # 2. Run the code (This will now pass because it's real ints/strings!)
    update_redis_state(real_feed, client)

    # 3. Assertions
    station_key = client.get_arrival_key(stop_id)
    score = client.client.zscore(station_key, trip_id)

    assert score == arrival_ts
