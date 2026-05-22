from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from transit_core.core.models import Coordinates
from transit_core.infrastructure.osrm_client import OsrmClient


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def osrm_client(mock_http_client):
    return OsrmClient(osrm_url="http://osrm.test/", http_client=mock_http_client)


async def test_get_walk_times_success(osrm_client, mock_http_client):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    stops = {
        1: Coordinates(lat=40.751, lon=-73.981),
        2: Coordinates(lat=40.752, lon=-73.982),
    }

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "code": "Ok",
        "durations": [[0, 300.5, 600.0]],
    }
    mock_http_client.get.return_value = mock_response

    result = await osrm_client.get_walk_times(user_loc, stops)

    assert result == {1: 300.5, 2: 600.0}
    mock_http_client.get.assert_called_once_with(
        "http://osrm.test/table/v1/foot/-73.98,40.75;-73.981,40.751;-73.982,40.752",
        params={"sources": 0},
    )


async def test_get_walk_times_empty_stops(osrm_client, mock_http_client):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    result = await osrm_client.get_walk_times(user_loc, {})
    assert result == {}
    mock_http_client.get.assert_not_called()


async def test_get_walk_times_http_status_error(osrm_client, mock_http_client):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    stops = {1: Coordinates(lat=40.751, lon=-73.981)}

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    error = httpx.HTTPStatusError("Error", request=AsyncMock(), response=mock_response)
    mock_http_client.get.side_effect = error

    with pytest.raises(httpx.HTTPStatusError):
        await osrm_client.get_walk_times(user_loc, stops)


async def test_get_walk_times_request_error(osrm_client, mock_http_client):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    stops = {1: Coordinates(lat=40.751, lon=-73.981)}

    mock_http_client.get.side_effect = httpx.RequestError("Network error")

    with pytest.raises(httpx.RequestError):
        await osrm_client.get_walk_times(user_loc, stops)


async def test_get_walk_times_key_error(osrm_client, mock_http_client):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    stops = {1: Coordinates(lat=40.751, lon=-73.981)}

    mock_response = MagicMock()
    # Missing 'durations' key
    mock_response.json.return_value = {"code": "Ok", "bad_data": []}
    mock_http_client.get.return_value = mock_response

    with pytest.raises(KeyError):
        await osrm_client.get_walk_times(user_loc, stops)


async def test_get_walk_times_generic_exception(osrm_client, mock_http_client):
    user_loc = Coordinates(lat=40.75, lon=-73.98)
    stops = {1: Coordinates(lat=40.751, lon=-73.981)}

    mock_http_client.get.side_effect = Exception("Unknown error")

    with pytest.raises(Exception):
        await osrm_client.get_walk_times(user_loc, stops)
