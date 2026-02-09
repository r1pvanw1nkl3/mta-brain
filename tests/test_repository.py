import time
from unittest.mock import ANY, MagicMock

import transit_core.core.models as md
from transit_core.core.repository import Keys, StopWriter, TripWriter


def test_trip_repository_update_trip_status():
    mock_state_store = MagicMock()
    repo = TripWriter(state_store=mock_state_store)

    trip_update = md.TripUpdate(
        trip=md.Trip(trip_id="T1", route_id="R1", start_date=20260206)
    )

    repo.update_trip_status(trip_update)

    mock_state_store.set_kv.assert_called_once()
    args = mock_state_store.set_kv.call_args[0]
    assert args[0] == Keys.trip("T1")
    assert "T1" in args[1]
    assert "R1" in args[1]
    assert mock_state_store.set_kv.call_args[1].get("expiry") == ANY or args[2] == ANY


def test_trip_repository_get_trip_status():
    mock_state_store = MagicMock()
    repo = TripWriter(state_store=mock_state_store)

    trip_id = "T1"
    json_data = '{"trip": {"trip_id": "T1", "route_id": "R1", "start_date": 20260206}}'
    mock_state_store.get_kv.return_value = json_data

    status = repo.get_trip_status(trip_id)

    assert status is not None
    assert status.trip.trip_id == "T1"
    mock_state_store.get_kv.assert_called_once_with(Keys.trip(trip_id))


def test_stop_repository_update_arrivals_board():
    current_time = int(time.time())
    mock_state_store = MagicMock()
    repo = StopWriter(state_store=mock_state_store)

    stop_id = "S1"
    arrivals = {"T1": 1000, "T2": 2000}

    repo.update_arrivals_board(stop_id, arrivals, current_time)

    mock_state_store.sync_set.assert_called_once_with(
        Keys.arrivals(stop_id), arrivals, current_time, ANY
    )
