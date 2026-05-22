from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import transit_core.core.models as md
from transit_core.api.dependencies import (
    get_planner_engine,
    get_stop_reader,
    get_trip_reader,
)
from transit_core.api.main import app
from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.repository import StopReader, TripReader


@pytest.fixture
def mock_stop_reader():
    return MagicMock(spec=StopReader)


@pytest.fixture
def mock_trip_reader():
    return MagicMock(spec=TripReader)


@pytest.fixture
def mock_planner_engine():
    return AsyncMock(spec=PlannerEngine)


@pytest.fixture
def client(mock_stop_reader, mock_trip_reader, mock_planner_engine):
    """Installs fresh dependency overrides per test and clears them on teardown.

    Instantiated without a context manager so the real app lifespan (which would
    open Redis/Postgres connections) never runs.
    """
    app.dependency_overrides[get_stop_reader] = lambda: mock_stop_reader
    app.dependency_overrides[get_trip_reader] = lambda: mock_trip_reader
    app.dependency_overrides[get_planner_engine] = lambda: mock_planner_engine
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_arrivals_stop(client, mock_stop_reader):
    now = 1700000000
    mock_stop_reader.get_arrivals_board.return_value = md.ArrivalsBoard(
        gtfs_stop_id="S1",
        stop_name="Stop 1",
        arrivals=[
            md.Arrival(
                trip_id="T1",
                route_id="1",
                headsign="Northbound",
                direction="N",
                arrival_time=now + 600,
                status="LIVE",
                is_realtime=True,
            )
        ],
    )

    response = client.get("/v1/stops/S1/arrivals")
    assert response.status_code == 200
    data = response.json()
    assert data["gtfs_stop_id"] == "S1"
    assert data["stop_name"] == "Stop 1"
    assert len(data["arrivals"]) == 1
    assert data["arrivals"][0]["trip_id"] == "T1"
    assert "minutes_away" in data["arrivals"][0]
    assert "clock_time" in data["arrivals"][0]


def test_get_trip_arrivals(client, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.return_value = [
        {
            "stop_id": "S1",
            "stop_name": "Stop 1",
            "arrival_time": 1000,
            "departure_time": 1050,
        }
    ]

    response = client.get("/v1/trips/T1/arrivals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["stop_name"] == "Stop 1"
    assert "arrival" in data[0]
    assert "departure" in data[0]


def test_get_trip_arrivals_not_found(client, mock_trip_reader):
    mock_trip_reader.get_trip_arrivals.return_value = []

    response = client.get("/v1/trips/T1/arrivals")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trip T1 not found"


def test_stop_search(client, mock_stop_reader):
    mock_stop_reader.fuzzy_station_search.return_value = [
        {"stop_id": "101", "stop_name": "242 St", "routes": "1", "rank": 1.0}
    ]

    response = client.get("/v1/stops/search?search_string=242")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["stop_id"] == "101"


def test_get_nearby_arrivals(client, mock_planner_engine):
    # Setup mock data for planner engine
    mock_planner_engine.get_nearby_arrivals.return_value = [
        md.ArrivalsBoard(
            gtfs_stop_id="A1",
            stop_name="Stop A",
            walk_time=10.0,
            arrivals=[
                md.Arrival(
                    trip_id="T1",
                    route_id="1",
                    headsign="Northbound",
                    direction="N",
                    arrival_time=1700000600,
                    status="LIVE",
                    is_realtime=True,
                )
            ],
        )
    ]

    response = client.get("/v1/planner/nearby?lat=40.75&lon=-73.98&max_walk_time=25")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["gtfs_stop_id"] == "A1"
    assert data[0]["walk_time"] == 10.0


def test_get_nearby_arrivals_not_found(client, mock_planner_engine):
    mock_planner_engine.get_nearby_arrivals.return_value = []

    response = client.get("/v1/planner/nearby?lat=40.75&lon=-73.98&max_walk_time=25")
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "No stops within range found for provided coordinates."
    )
