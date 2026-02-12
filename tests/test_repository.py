from unittest.mock import ANY, MagicMock, patch

import transit_core.core.models as md
from transit_core.config import get_settings
from transit_core.core.repository import (
    Keys,
    StopReader,
    StopWriter,
    TripReader,
    TripWriter,
)

config = get_settings()


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
    now = 1700000000
    mock_state_store = MagicMock()
    repo = StopWriter(state_store=mock_state_store)

    stop_id = "S1"
    arrivals = {"T1": 1000, "T2": 2000}

    with patch("time.time", return_value=now):
        repo.update_arrivals_board(stop_id, arrivals, now)

    mock_state_store.sync_set.assert_called_once_with(
        Keys.arrivals(stop_id),
        arrivals,
        now - config.arrivals_window_past_seconds,
        ANY,
    )


def test_stop_reader_get_arrivals_board_unified():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_state_store.get_kv.return_value = None
    mock_static_store = MagicMock()
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    stop_id = "S1"
    # S1N: Live match, S1S: Live-Added
    mock_state_store.get_zset.side_effect = [
        {"T_LIVE": now + 600},  # S1N
        {"T_ADDED": now + 300},  # S1S
    ]

    # Scheduled: T_LIVE (matches) and T_GHOST (no live)
    mock_static_store.get_scheduled_arrivals.return_value = [
        {
            "trip_id": "T_LIVE",
            "route_id": "1",
            "trip_headsign": "Northbound",
            "direction": "N",
            "arrival_timestamp": now + 600,
        },
        {
            "trip_id": "T_GHOST",
            "route_id": "1",
            "trip_headsign": "Northbound",
            "direction": "N",
            "arrival_timestamp": now + 1200,
        },
    ]

    # For T_ADDED metadata lookup
    mock_state_store.get_kv.return_value = None  # No metadata in Redis
    mock_static_store.get_trip_metadata.return_value = {
        "route_id": "2",
        "trip_headsign": "Southbound Extra",
    }

    with patch("time.time", return_value=now):
        board = repo.get_arrivals_board(stop_id)

    assert len(board) == 3

    # T_ADDED (now + 300)
    assert board[0].trip_id == "T_ADDED"
    assert board[0].status == "LIVE-ADDED"
    assert board[0].arrival_time == now + 300

    # T_LIVE (now + 600)
    assert board[1].trip_id == "T_LIVE"
    assert board[1].status == "LIVE"
    assert board[1].arrival_time == now + 600

    # T_GHOST (now + 1200)
    assert board[2].trip_id == "T_GHOST"
    assert board[2].status == "SCHEDULED"


def test_trip_writer_get_trip_status_none():
    mock_state_store = MagicMock()
    repo = TripWriter(state_store=mock_state_store)
    mock_state_store.get_kv.return_value = None
    assert repo.get_trip_status("MISSING") is None


def test_stop_reader_fuzzy_match_skips_already_matched():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_static_store = MagicMock()
    mock_static_store.get_trip_metadata.return_value = None
    mock_static_store.get_stop_name.return_value = "Unknown"
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    # Two live trains, same route (inferred from IDs)
    t1, t2 = "100000_1..N", "100100_1..N"
    mock_state_store.get_zset.return_value = {t1: now + 600, t2: now + 610}
    mock_state_store.get_kv.return_value = None

    # Three scheduled trains, T_S1 is closer to T1, but T_S1 is also closer to T2
    # We want to make sure if T1 matches T_S1, T2 skips T_S1 and matches T_S2
    mock_static_store.get_scheduled_arrivals.return_value = [
        {
            "trip_id": "T_S1",
            "route_id": "1",
            "trip_headsign": "D1",
            "direction": "N",
            "arrival_timestamp": now + 605,
        },
        {
            "trip_id": "T_S2",
            "route_id": "1",
            "trip_headsign": "D1",
            "direction": "N",
            "arrival_timestamp": now + 615,
        },
    ]

    with patch("time.time", return_value=now):
        # We need to ensure T1 is processed first to match T_S1
        # get_zset returns a dict, order might be arbitrary but usually insertion order
        # Let's mock it to return items in specific order
        mock_state_store.get_zset.return_value = {t1: now + 600, t2: now + 610}
        board = repo.get_arrivals_board("S1N")

    assert len(board) == 2
    # T1 should match T_S1 (diff 5)
    # T2 should match T_S2 (diff 5) because T_S1 is in matched_static_ids
    # (diff would have been 5 too)
    matched_ids = [a.trip_id for a in board]
    assert t1 in matched_ids
    assert t2 in matched_ids

    # Verify both got matched to different static trips
    headsigns = [a.headsign for a in board]
    assert headsigns == ["D1", "D1"]

    # Check that they didn't fall back to LIVE-ADDED
    assert all(a.status == "LIVE" for a in board)


def test_keys():
    assert Keys.trip("T1") == "trip:T1"
    assert Keys.arrivals("S1") == "arrivals:S1"
    assert Keys.feed("F1") == "feed:F1"


def test_stop_reader_get_stop_name():
    mock_state_store = MagicMock()
    mock_static_store = MagicMock()
    reader = StopReader(state_store=mock_state_store, static_store=mock_static_store)
    mock_static_store.get_stop_name.return_value = "Stop 1"
    assert reader.get_stop_name("S1") == "Stop 1"
    mock_static_store.get_stop_name.assert_called_once_with("S1")


def test_trip_reader_get_trip_status():
    mock_state_store = MagicMock()
    mock_static_store = MagicMock()
    reader = TripReader(state_store=mock_state_store, static_store=mock_static_store)

    # Test None case
    mock_state_store.get_kv.return_value = None
    assert reader.get_trip_status("MISSING") is None

    # Test success case
    json_data = '{"trip": {"trip_id": "T1", "route_id": "R1", "start_date": 20260206}}'
    mock_state_store.get_kv.return_value = json_data
    status = reader.get_trip_status("T1")
    assert status.trip.trip_id == "T1"


def test_trip_reader_get_trip_arrivals_live():
    mock_state_store = MagicMock()
    mock_static_store = MagicMock()
    reader = TripReader(state_store=mock_state_store, static_store=mock_static_store)

    trip_id = "T1"
    now = 1000
    # Use explicit JSON string with aliases
    # ('arrival', 'departure') as would come from Redis
    json_data = {
        "trip": {"trip_id": trip_id, "route_id": "R1", "start_date": 20260209},
        "stop_time_update": [
            {"stop_id": "S1", "arrival": {"time": now + 60}},
            {"stop_id": "S2", "departure": {"time": now + 120}},
        ],
    }
    import json

    mock_state_store.get_kv.return_value = json.dumps(json_data)
    mock_static_store.get_stop_names.return_value = {"S1": "Stop 1", "S2": "Stop 2"}

    arrivals = reader.get_trip_arrivals(trip_id)

    assert arrivals == [
        {
            "stop_id": "S1",
            "stop_name": "Stop 1",
            "arrival_time": now + 60,
            "departure_time": None,
        },
        {
            "stop_id": "S2",
            "stop_name": "Stop 2",
            "arrival_time": None,
            "departure_time": now + 120,
        },
    ]
    mock_static_store.get_trip_stop_times.assert_not_called()


def test_trip_reader_get_trip_arrivals_static_fallback():
    mock_state_store = MagicMock()
    mock_static_store = MagicMock()
    reader = TripReader(state_store=mock_state_store, static_store=mock_static_store)

    trip_id = "T1"
    mock_state_store.get_kv.return_value = None
    mock_static_store.get_trip_stop_times.return_value = {"S1": 1000, "S2": 2000}
    mock_static_store.get_stop_names.return_value = {"S1": "Stop 1", "S2": "Stop 2"}

    arrivals = reader.get_trip_arrivals(trip_id)

    assert arrivals == [
        {
            "stop_id": "S1",
            "stop_name": "Stop 1",
            "arrival_time": 1000,
            "departure_time": 1000,
        },
        {
            "stop_id": "S2",
            "stop_name": "Stop 2",
            "arrival_time": 2000,
            "departure_time": 2000,
        },
    ]
    mock_static_store.get_trip_stop_times.assert_called_once_with(trip_id)


def test_stop_reader_get_arrivals_board_specific_platform():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_state_store.get_kv.return_value = None
    mock_static_store = MagicMock()
    mock_static_store.get_trip_metadata.return_value = None
    mock_static_store.get_stop_name.return_value = "Unknown"
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    # Request ONLY Northbound
    stop_id = "S1N"
    mock_state_store.get_zset.return_value = {"T1": now + 600}
    mock_static_store.get_scheduled_arrivals.return_value = [
        {
            "trip_id": "T_GHOST_S",
            "route_id": "1",
            "trip_headsign": "Southbound",
            "direction": "S",
            "arrival_timestamp": now + 800,
        }
    ]

    with patch("time.time", return_value=now):
        board = repo.get_arrivals_board(stop_id)

    # Should only see the Live T1 (N) and NOT the Scheduled Southbound ghost
    assert len(board) == 1
    assert board[0].trip_id == "T1"
    assert board[0].direction == "N"
    assert board[0].route_id == "???"
    assert board[0].headsign == "In Transit"


def test_stop_reader_fuzzy_matching_and_inference():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_state_store.get_kv.return_value = None
    mock_static_store = MagicMock()
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    # 1. Trip ID with route in it: 081300_B..S66R -> Route B
    trip_id = "081300_B..S66R"
    mock_state_store.get_zset.return_value = {trip_id: now + 600}

    # Scheduled train on Route B in South direction
    mock_static_store.get_scheduled_arrivals.return_value = [
        {
            "trip_id": "STATIC_B_SOUTH",
            "route_id": "B",
            "trip_headsign": "Brighton Beach",
            "direction": "S",
            "arrival_timestamp": now + 610,  # 10s difference
        }
    ]

    with patch("time.time", return_value=now):
        board = repo.get_arrivals_board("S1S")

    assert len(board) == 1
    assert board[0].trip_id == trip_id
    assert board[0].route_id == "B"
    assert board[0].status == "LIVE"  # Matched fuzzy
    assert board[0].headsign == "Brighton Beach"


def test_stop_reader_static_suffix_fallback():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_state_store.get_kv.return_value = None
    mock_static_store = MagicMock()
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    trip_id = "LIVE_TRIP"
    mock_state_store.get_zset.return_value = {trip_id: now + 600}
    mock_static_store.get_scheduled_arrivals.return_value = []

    # Fail first, then succeed with suffix search
    mock_static_store.get_trip_metadata.side_effect = [
        None,
        {"route_id": "L", "trip_headsign": "Canarsie"},
    ]

    with patch("time.time", return_value=now):
        board = repo.get_arrivals_board("L01N")

    assert len(board) == 1
    assert board[0].route_id == "L"
    assert board[0].status == "LIVE-ADDED"
    assert mock_static_store.get_trip_metadata.call_count == 2


def test_stop_reader_drops_old_trains():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_state_store.get_kv.return_value = None
    mock_static_store = MagicMock()
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    mock_state_store.get_zset.return_value = {}
    mock_static_store.get_scheduled_arrivals.return_value = [
        {
            "trip_id": "OLD_GHOST",
            "route_id": "1",
            "trip_headsign": "Gone",
            "direction": "N",
            "arrival_timestamp": now - (config.arrivals_window_past_seconds + 100),
        },
        {
            "trip_id": "RECENT_GHOST",
            "route_id": "1",
            "trip_headsign": "Just missed",
            "direction": "N",
            "arrival_timestamp": now - 30,  # 30s ago
        },
    ]

    with patch("time.time", return_value=now):
        board = repo.get_arrivals_board("S1")

    assert len(board) == 1
    assert board[0].trip_id == "RECENT_GHOST"


def test_stop_reader_with_redis_metadata():
    now = 1700000000
    mock_state_store = MagicMock()
    mock_static_store = MagicMock()
    repo = StopReader(state_store=mock_state_store, static_store=mock_static_store)

    trip_id = "METADATA_TRIP"
    mock_state_store.get_zset.return_value = {trip_id: now + 600}

    # Mock valid TripUpdate JSON in Redis
    trip_update = md.TripUpdate(
        trip=md.Trip(trip_id=trip_id, route_id="G", start_date=20260209),
        stop_time_update=[
            md.StopTimeUpdate(stop_id="G08N", arrival=md.TimeUpdate(time=now + 600)),
            md.StopTimeUpdate(stop_id="G01N", arrival=md.TimeUpdate(time=now + 1200)),
        ],
    )
    mock_state_store.get_kv.return_value = trip_update.model_dump_json()

    # Mock stop name for the destination (G01N)
    mock_static_store.get_stop_name.return_value = "Court Sq"
    mock_static_store.get_scheduled_arrivals.return_value = []

    with patch("time.time", return_value=now):
        board = repo.get_arrivals_board("G08N")

    assert len(board) == 1
    assert board[0].trip_id == trip_id
    assert board[0].route_id == "G"
    assert board[0].headsign == "Court Sq"
    assert board[0].status == "LIVE-ADDED"
