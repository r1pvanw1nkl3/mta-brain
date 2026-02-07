from unittest.mock import MagicMock, patch

from services.subway_live_hydrator.state_manager import hydrate_realtime_data


def create_mock_feed(num_stops=2, arrival_time=1700000000):
    mock_entity = MagicMock()
    mock_entity.trip_update.trip.trip_id = "test_trip_1"

    stops = []
    for i in range(num_stops):
        stop = MagicMock()
        stop.stop_id = f"G08{i}"
        stop.arrival_time.time = arrival_time + (i * 60)
        stop.departure_time = None
        stops.append(stop)

    mock_entity.trip_update.stop_time_update = stops

    mock_feed = MagicMock()
    mock_feed.entity = [mock_entity]
    return mock_feed


def test_hydrate_realtime_data_calls_repositories():
    # Setup mocks
    mock_trip_repo = MagicMock()
    mock_stop_repo = MagicMock()
    mock_state_store = MagicMock()
    mock_trip_repo.state_store = mock_state_store

    num_stops = 3
    arrival_time = 1700000000
    feed = create_mock_feed(num_stops=num_stops, arrival_time=arrival_time)

    # Mock time to be before the arrivals
    with patch("time.time", return_value=arrival_time - 100):
        hydrate_realtime_data(feed, mock_trip_repo, mock_stop_repo)

    # Verify trip_repo.update_trip_status was called
    mock_trip_repo.update_trip_status.assert_called_once_with(
        feed.entity[0].trip_update
    )

    # Verify stop_repo.arrivals was called
    # Since all stops are for the same trip,
    # they should be aggregated into their respective boards
    assert mock_stop_repo.update_arrivals_board.call_count == num_stops

    # Verify batch_session was used
    mock_state_store.batch_session.assert_called_once()


def test_hydrate_realtime_data_filters_past_arrivals():
    mock_trip_repo = MagicMock()
    mock_stop_repo = MagicMock()
    mock_state_store = MagicMock()
    mock_trip_repo.state_store = mock_state_store

    arrival_time = 1700000000
    feed = create_mock_feed(num_stops=1, arrival_time=arrival_time)

    # Mock time to be AFTER the arrival
    with patch("time.time", return_value=arrival_time + 100):
        hydrate_realtime_data(feed, mock_trip_repo, mock_stop_repo)

    # Trip status should still be updated
    mock_trip_repo.update_trip_status.assert_called_once()

    # Arrivals board should NOT be updated because the stop is in the past
    mock_stop_repo.update_arrivals_board.assert_not_called()


def test_hydrate_realtime_data_aggregates_multiple_trips_to_same_stop():
    mock_trip_repo = MagicMock()
    mock_stop_repo = MagicMock()
    mock_state_store = MagicMock()
    mock_trip_repo.state_store = mock_state_store

    stop_id = "STOP_X"
    current_time = 1700000000

    # Create two entities (trips) for the same stop
    entity1 = MagicMock()
    entity1.trip_update.trip.trip_id = "trip1"
    stop_time1 = MagicMock()
    stop_time1.stop_id = stop_id
    stop_time1.arrival_time.time = current_time + 100
    stop_time1.departure_time = None
    entity1.trip_update.stop_time_update = [stop_time1]

    entity2 = MagicMock()
    entity2.trip_update.trip.trip_id = "trip2"
    stop_time2 = MagicMock()
    stop_time2.stop_id = stop_id
    stop_time2.arrival_time.time = current_time + 200
    stop_time2.departure_time = None
    entity2.trip_update.stop_time_update = [stop_time2]

    feed = MagicMock()
    feed.entity = [entity1, entity2]

    with patch("time.time", return_value=current_time):
        hydrate_realtime_data(feed, mock_trip_repo, mock_stop_repo)

    # Should call update_arrivals_board ONCE for STOP_X with both trips
    mock_stop_repo.update_arrivals_board.assert_called_once()
    args = mock_stop_repo.update_arrivals_board.call_args[0]
    assert args[0] == stop_id
    assert args[1] == {
        "trip1": current_time + 100,
        "trip2": current_time + 200,
    }
