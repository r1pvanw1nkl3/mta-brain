from unittest.mock import ANY, MagicMock, patch

from services.subway_live_hydrator.state_manager import update_redis_state


def create_mock_feed(num_stops=2):
    mock_entity = MagicMock()
    mock_entity.trip_update.trip.trip_id = "test_trip_1"
    mock_entity.trip_update.model_dump_json.return_value = '{"id": "test"}'

    stops = []
    for i in range(num_stops):
        stop = MagicMock()
        stop.stop_id = f"G08{i}"
        stop.arrival.time = 1700000000 + (i * 60)
        stops.append(stop)

    mock_entity.trip_update.stop_time_update = stops

    mock_feed = MagicMock()
    mock_feed.entity = [mock_entity]
    return mock_feed


def test_update_redis_state_pivot_logic():
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.get_redis_pipeline.return_value.__enter__.return_value = mock_pipe

    num_stops = 3
    feed = create_mock_feed(num_stops=num_stops)

    update_redis_state(feed, mock_redis)

    assert mock_pipe.set.called

    assert mock_pipe.zadd.call_count == num_stops

    assert mock_pipe.expire.called


def test_update_redis_state_janitor_call():
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.get_redis_pipeline.return_value.__enter__.return_value = mock_pipe

    feed = create_mock_feed(num_stops=1)

    fixed_now = 1600000000
    with patch("time.time", return_value=fixed_now):
        update_redis_state(feed, mock_redis)

    mock_pipe.zremrangebyscore.assert_called_with(
        ANY,
        0,
        fixed_now,
    )
