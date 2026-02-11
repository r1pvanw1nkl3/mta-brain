from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from transit_core.infrastructure.static_store import PostgresStaticStore


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = MagicMock()
    pool.connection.return_value.__enter__.return_value = conn
    return pool, conn


def test_get_stop_name(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value.fetchone.return_value = {"stop_name": "Times Sq"}

    store = PostgresStaticStore(pool)
    assert store.get_stop_name("123N") == "Times Sq"
    conn.execute.assert_called_once()
    # Check that it stripped N
    assert conn.execute.call_args[0][1] == ("123",)


def test_get_stop_name_unknown(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value.fetchone.return_value = None

    store = PostgresStaticStore(pool)
    assert store.get_stop_name("999") == "Unknown"


def test_get_stop_names(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value = [{"stop_id": "S1", "stop_name": "Stop 1"}]

    store = PostgresStaticStore(pool)
    names = store.get_stop_names(["S1"])
    assert names == {"S1": "Stop 1"}


def test_get_trip_metadata(mock_pool):
    pool, conn = mock_pool
    row = {"trip_id": "T1", "route_id": "1", "trip_headsign": "H1", "direction": "N"}
    conn.execute.return_value.fetchone.return_value = row

    store = PostgresStaticStore(pool)
    meta = store.get_trip_metadata("T1")
    assert meta == row


def test_get_trip_stop_times(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value.fetchall.side_effect = [
        [{"stop_id": "S1", "arrival_time": timedelta(hours=8)}],
        [],  # for suffix match if first fails
    ]

    store = PostgresStaticStore(pool)
    # Mock _to_epoch to return a fixed value
    store._to_epoch = MagicMock(return_value=12345)

    times = store.get_trip_stop_times("T1")
    assert times == {"S1": 12345}


def test_get_scheduled_arrivals(mock_pool):
    pool, conn = mock_pool
    row = {
        "trip_id": "T1",
        "arrival_time": timedelta(hours=8),
        "route_id": "1",
        "trip_headsign": "H1",
        "platform_id": "S1N",
        "direction": "N",
    }
    conn.execute.return_value.fetchall.return_value = [row]

    store = PostgresStaticStore(pool)
    store._to_epoch = MagicMock(return_value=12345)

    arrivals = store.get_scheduled_arrivals("S1", 60)
    assert len(arrivals) == 1
    assert arrivals[0]["arrival_timestamp"] == 12345
    assert arrivals[0]["trip_id"] == "T1"


def test_get_trip_stop_times_suffix_fallback(mock_pool):
    pool, conn = mock_pool
    conn.execute.return_value.fetchall.side_effect = [
        [],  # First query fails
        [
            {"stop_id": "S1", "arrival_time": timedelta(hours=8)}
        ],  # Suffix match succeeds
    ]

    store = PostgresStaticStore(pool)
    times = store.get_trip_stop_times("T1")
    assert "S1" in times


def test_to_epoch():
    store = PostgresStaticStore(MagicMock())
    delta = timedelta(hours=1)
    epoch = store._to_epoch(delta)
    assert isinstance(epoch, int)
    assert epoch > 0


def test_get_scheduled_arrivals_exception(mock_pool):
    pool, conn = mock_pool
    conn.execute.side_effect = Exception("DB Error")
    store = PostgresStaticStore(pool)
    assert store.get_scheduled_arrivals("S1", 60) == []


def test_get_trip_metadata_exception(mock_pool):
    pool, conn = mock_pool
    conn.execute.side_effect = Exception("DB Error")
    store = PostgresStaticStore(pool)
    assert store.get_trip_metadata("T1") is None


def test_get_stop_name_exception(mock_pool):
    pool, conn = mock_pool
    conn.execute.side_effect = Exception("DB Error")
    store = PostgresStaticStore(pool)
    assert store.get_stop_name("S1") == "Unknown"


def test_get_trip_stop_times_exception(mock_pool):
    pool, conn = mock_pool
    conn.execute.side_effect = Exception("DB Error")
    store = PostgresStaticStore(pool)
    assert store.get_trip_stop_times("T1") == {}
