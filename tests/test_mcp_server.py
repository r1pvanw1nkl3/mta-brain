from unittest.mock import MagicMock, patch

import pytest

import transit_core.core.models as md
from transit_core.mcp.server import (
    get_station_info,
    get_trip_arrivals,
    lifespan,
    station_search,
)


@pytest.fixture
def mock_stop_reader():
    return MagicMock()


@pytest.fixture
def mock_trip_reader():
    return MagicMock()


@pytest.fixture
def mock_ctx(mock_stop_reader, mock_trip_reader):
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {
        "stop_reader": mock_stop_reader,
        "trip_reader": mock_trip_reader,
    }
    return ctx


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
        result = get_station_info.fn("101N", mock_ctx)

    assert len(result) == 1
    assert result[0]["route"] == "1"
    assert result[0]["destination"] == "Van Cortlandt Park"
    assert result[0]["minutes_away"] == 5
    assert result[0]["status"] == "LIVE"
    assert result[0]["trip_id"] == "T1"


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
        result = get_station_info.fn("101N", mock_ctx)

    assert result[0]["minutes_away"] == 0


def test_get_station_info_no_data(mock_ctx, mock_stop_reader):
    mock_stop_reader.get_arrivals_board.return_value = []

    result = get_station_info.fn("101N", mock_ctx)
    assert result == []


def test_get_station_info_error(mock_ctx, mock_stop_reader):
    mock_stop_reader.get_arrivals_board.side_effect = Exception("DB Error")

    with pytest.raises(Exception) as excinfo:
        get_station_info.fn("101N", mock_ctx)
    assert "DB Error" in str(excinfo.value)


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
        result = get_trip_arrivals.fn("T1", mock_ctx)

    assert len(result) == 1
    assert result[0]["stop_id"] == "101N"
    assert result[0]["stop_name"] == "242 St"
    assert result[0]["minutes_away"] == 1


def test_get_trip_arrivals_no_data(mock_ctx, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.return_value = []

    result = get_trip_arrivals.fn("T1", mock_ctx)
    assert result == []


def test_get_trip_arrivals_no_time(mock_ctx, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.return_value = [
        {
            "stop_id": "101N",
            "stop_name": "242 St",
            "arrival_time": None,
            "departure_time": None,
        }
    ]

    result = get_trip_arrivals.fn("T1", mock_ctx)
    assert result[0]["minutes_away"] is None
    assert result[0]["time_display"] == "N/A"


def test_get_trip_arrivals_error(mock_ctx, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.side_effect = Exception("Redis Error")

    with pytest.raises(Exception) as excinfo:
        get_trip_arrivals.fn("T1", mock_ctx)
    assert "Redis Error" in str(excinfo.value)


def test_station_search_success(mock_ctx, mock_stop_reader):
    mock_stop_reader.fuzzy_station_search.return_value = [
        {"stop_id": "101", "stop_name": "242 St", "routes": "1", "rank": 1.0}
    ]

    result = station_search.fn("242 St", mock_ctx)

    assert len(result) == 1
    assert result[0]["stop_id"] == "101"
    assert result[0]["stop_name"] == "242 St"


def test_station_search_error(mock_ctx, mock_stop_reader):
    mock_stop_reader.fuzzy_station_search.side_effect = Exception("Search Error")

    result = station_search.fn("242 St", mock_ctx)
    assert result is None


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
