from unittest.mock import MagicMock, patch

import pytest

import transit_core.core.models as md
from transit_core.mcp.server import get_station_info, get_trip_arrivals, lifespan


class MockRequestContext:
    def __init__(self, lifespan_context):
        self.lifespan_context = lifespan_context


class MockContext:
    def __init__(self, lifespan_context):
        self.request_context = MockRequestContext(lifespan_context)


@pytest.fixture
def mock_stop_reader():
    return MagicMock()


@pytest.fixture
def mock_trip_reader():
    return MagicMock()


@pytest.fixture
def mock_ctx(mock_stop_reader, mock_trip_reader):
    return MockContext(
        {"stop_reader": mock_stop_reader, "trip_reader": mock_trip_reader}
    )


def test_get_station_info_success(mock_ctx, mock_stop_reader):
    now = 1700000000
    mock_stop_reader.get_arrivals_board.return_value = [
        md.Arrival(
            trip_id="T1",
            route_id="1",
            headsign="Van Cortlandt Park",
            arrival_time=now + 300,
            status="LIVE",
            direction="N",
            is_realtime=True,
        )
    ]

    with patch("time.time", return_value=now):
        result = get_station_info("101N", mock_ctx)

    assert "1 to Van Cortlandt Park: 5m" in result
    assert "[LIVE]" in result
    assert "[Trip ID: T1]" in result


def test_get_station_info_past_arrival(mock_ctx, mock_stop_reader):
    now = 1700000000
    mock_stop_reader.get_arrivals_board.return_value = [
        md.Arrival(
            trip_id="T1",
            route_id="1",
            headsign="Van Cortlandt Park",
            arrival_time=now - 60,
            status="LIVE",
            direction="N",
            is_realtime=True,
        )
    ]

    with patch("time.time", return_value=now):
        result = get_station_info("101N", mock_ctx)

    assert "1 to Van Cortlandt Park: 0m" in result


def test_get_station_info_no_data(mock_ctx, mock_stop_reader):
    mock_stop_reader.get_arrivals_board.return_value = []

    result = get_station_info("101N", mock_ctx)
    assert "No arrival data found for stop 101N" in result


def test_get_station_info_error(mock_ctx, mock_stop_reader):
    mock_stop_reader.get_arrivals_board.side_effect = Exception("DB Error")

    result = get_station_info("101N", mock_ctx)
    assert "Error fetching station info: DB Error" in result


def test_get_trip_arrivals_success(mock_ctx, mock_trip_reader):
    now = 1700000000
    mock_trip_reader.get_trip_arrivals.return_value = [
        {
            "stop_id": "101N",
            "stop_name": "242 St",
            "arrival_time": now + 60,
            "departure_time": now + 60,
        }
    ]

    with patch("time.time", return_value=now):
        result = get_trip_arrivals("T1", mock_ctx)

    assert "242 St (101N): 1m" in result


def test_get_trip_arrivals_no_data(mock_ctx, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.return_value = []

    result = get_trip_arrivals("T1", mock_ctx)
    assert "No arrival data found for trip T1" in result


def test_get_trip_arrivals_no_time(mock_ctx, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.return_value = [
        {
            "stop_id": "101N",
            "stop_name": "242 St",
            "arrival_time": None,
            "departure_time": None,
        }
    ]

    result = get_trip_arrivals("T1", mock_ctx)
    assert "242 St (101N): N/A" in result


def test_get_trip_arrivals_error(mock_ctx, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.side_effect = Exception("Redis Error")

    result = get_trip_arrivals("T1", mock_ctx)
    assert "Error fetching trip arrivals: Redis Error" in result


@pytest.mark.anyio
async def test_lifespan():
    mock_server = MagicMock()
    mock_redis = MagicMock()
    mock_pool = MagicMock()

    with (
        patch("transit_core.mcp.server.RedisClient", return_value=mock_redis),
        patch("transit_core.mcp.server.create_db_pool", return_value=mock_pool),
        patch("transit_core.mcp.server.RedisStateStore"),
        patch("transit_core.mcp.server.PostgresStaticStore"),
        patch("transit_core.mcp.server.StopReader"),
        patch("transit_core.mcp.server.TripReader"),
    ):
        async with lifespan(mock_server) as readers:
            assert "stop_reader" in readers
            assert "trip_reader" in readers

        mock_pool.close.assert_called_once()
        mock_redis.client.close.assert_called_once()
