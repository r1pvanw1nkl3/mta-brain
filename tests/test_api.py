from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import transit_core.core.models as md
from transit_core.api.dependencies import get_stop_reader, get_trip_reader
from transit_core.api.main import app
from transit_core.core.repository import StopReader, TripReader

# Mock readers
mock_stop_reader = MagicMock(spec=StopReader)
mock_trip_reader = MagicMock(spec=TripReader)


def override_get_stop_reader():
    return mock_stop_reader


def override_get_trip_reader():
    return mock_trip_reader


app.dependency_overrides[get_stop_reader] = override_get_stop_reader
app.dependency_overrides[get_trip_reader] = override_get_trip_reader

client = TestClient(app)


def test_get_arrivals_stop():
    now = 1700000000
    mock_stop_reader.get_arrivals_board.return_value = [
        md.Arrival(
            trip_id="T1",
            route_id="1",
            headsign="Northbound",
            direction="N",
            arrival_time=now + 600,
            status="LIVE",
            is_realtime=True,
        )
    ]

    response = client.get("/stops/S1/arrivals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["trip_id"] == "T1"
    assert "minutes_away" in data[0]
    assert "clock_time" in data[0]


def test_get_trip_arrivals():
    mock_trip_reader.get_trip_arrivals.return_value = [
        {
            "stop_id": "S1",
            "stop_name": "Stop 1",
            "arrival_time": 1000,
            "departure_time": 1050,
        }
    ]

    response = client.get("/trips/T1/arrivals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["stop_name"] == "Stop 1"
    assert "arrival" in data[0]
    assert "departure" in data[0]


def test_get_trip_arrivals_not_found():
    mock_trip_reader.get_trip_arrivals.return_value = []

    response = client.get("/trips/T1/arrivals")
    assert response.status_code == 404
    assert response.json()["detail"] == "Trip T1 not found"


def test_get_trip_status():
    mock_trip_reader.get_trip_status.return_value = md.TripUpdate(
        trip=md.Trip(trip_id="T1", route_id="1", start_date=20260211)
    )

    response = client.get("/trips/T1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["trip"]["trip_id"] == "T1"


def test_get_trip_status_none():
    mock_trip_reader.get_trip_status.return_value = None

    response = client.get("/trips/T1/status")
    assert response.status_code == 200
    assert response.json() is None


def test_stop_search():
    mock_stop_reader.fuzzy_station_search.return_value = [
        {"stop_id": "101", "stop_name": "242 St", "routes": "1", "rank": 1.0}
    ]

    response = client.get("/stops/search/242")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["stop_id"] == "101"
