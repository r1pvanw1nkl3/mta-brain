from unittest.mock import AsyncMock, MagicMock

import pytest

from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.interfaces import StreetRoutingService
from transit_core.core.models import Arrival, Coordinates, NearbyStop
from transit_core.core.repository import StopReader


@pytest.fixture
def mock_stop_reader():
    return MagicMock(spec=StopReader)


@pytest.fixture
def mock_routing_service():
    return AsyncMock(spec=StreetRoutingService)


@pytest.fixture
def planner_engine(mock_stop_reader, mock_routing_service):
    return PlannerEngine(
        stop_reader=mock_stop_reader, routing_service=mock_routing_service
    )


@pytest.mark.asyncio
async def test_get_nearby_arrivals(
    planner_engine, mock_stop_reader, mock_routing_service
):
    user_loc = Coordinates(lat=40.75, lon=-73.98)

    # Mock stop reader returning two stops
    mock_stop_reader.get_nearby_stops.return_value = [
        NearbyStop(
            id=1,
            stop_name="Stop A",
            gtfs_stop_id="A1",
            line="A",
            coordinates=Coordinates(lat=40.751, lon=-73.981),
            dist_meters=100.0,
        ),
        NearbyStop(
            id=2,
            stop_name="Stop B",
            gtfs_stop_id="B1",
            line="B",
            coordinates=Coordinates(lat=40.752, lon=-73.982),
            dist_meters=200.0,
        ),
    ]

    # Mock routing service returning durations in seconds (10 mins and 30 mins)
    mock_routing_service.get_walk_times.return_value = {1: 600.0, 2: 1800.0}

    # Mock arrivals
    mock_stop_reader.get_arrivals_board.return_value = [
        Arrival(
            trip_id="T1",
            route_id="1",
            headsign="Northbound",
            direction="N",
            arrival_time=1700000600,
            status="LIVE",
            is_realtime=True,
        )
    ]

    # Test with max walk time 25 minutes
    boards = await planner_engine.get_nearby_arrivals(user_loc, max_walk_time_mins=25)

    # Stop A (10 mins) should be included, Stop B (30 mins) should be filtered out
    assert len(boards) == 1
    assert boards[0].gtfs_stop_id == "A1"
    assert boards[0].walk_time == 10.0
    assert boards[0].stop_name == "Stop A"
    assert len(boards[0].arrivals) == 1

    # Verify calls
    mock_stop_reader.get_nearby_stops.assert_called_once_with(user_loc, 25)
    mock_routing_service.get_walk_times.assert_called_once()


@pytest.mark.asyncio
async def test_get_nearby_arrivals_no_stops(
    planner_engine, mock_stop_reader, mock_routing_service
):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    mock_stop_reader.get_nearby_stops.return_value = []
    mock_routing_service.get_walk_times.return_value = {}

    boards = await planner_engine.get_nearby_arrivals(user_loc)
    assert boards == []
