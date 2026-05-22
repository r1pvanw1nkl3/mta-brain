from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from transit_core.infrastructure.census_gc_client import CensusGCClient


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def gc_client(mock_http_client):
    return CensusGCClient(
        geocoding_url="http://census.test/geocode", http_client=mock_http_client
    )


def _match_response(matches):
    response = MagicMock()
    response.json.return_value = {"result": {"addressMatches": matches}}
    return response


async def test_get_coords_success(gc_client, mock_http_client):
    mock_http_client.get.return_value = _match_response(
        [
            {
                "matchedAddress": "350 5TH AVE, NEW YORK, NY, 10118",
                "coordinates": {"x": -73.985, "y": 40.748},
            }
        ]
    )

    result = await gc_client.get_coords("350 5th Ave")

    assert result is not None
    assert result.matched_address == "350 5TH AVE, NEW YORK, NY, 10118"
    # Census returns x=lon, y=lat; verify the mapping isn't swapped.
    assert result.coords.lon == -73.985
    assert result.coords.lat == 40.748

    mock_http_client.get.assert_called_once_with(
        "http://census.test/geocode",
        params={
            "address": "350 5th Ave",
            "benchmark": "Public_AR_Current",
            "format": "json",
        },
    )


async def test_get_coords_no_matches_returns_none(gc_client, mock_http_client):
    mock_http_client.get.return_value = _match_response([])
    assert await gc_client.get_coords("nowhere at all") is None


async def test_get_coords_uses_first_match(gc_client, mock_http_client):
    mock_http_client.get.return_value = _match_response(
        [
            {
                "matchedAddress": "FIRST",
                "coordinates": {"x": -73.1, "y": 40.1},
            },
            {
                "matchedAddress": "SECOND",
                "coordinates": {"x": -73.2, "y": 40.2},
            },
        ]
    )

    result = await gc_client.get_coords("ambiguous")

    assert result is not None
    assert result.matched_address == "FIRST"


async def test_get_coords_http_status_error_raises(gc_client, mock_http_client):
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom", request=MagicMock(), response=MagicMock()
    )
    mock_http_client.get.return_value = response

    with pytest.raises(httpx.HTTPStatusError):
        await gc_client.get_coords("350 5th Ave")


async def test_get_coords_request_error_raises(gc_client, mock_http_client):
    mock_http_client.get.side_effect = httpx.RequestError("network down")

    with pytest.raises(httpx.RequestError):
        await gc_client.get_coords("350 5th Ave")


async def test_get_coords_malformed_payload_raises(gc_client, mock_http_client):
    response = MagicMock()
    # Missing the "result"/"addressMatches" structure.
    response.json.return_value = {"unexpected": "shape"}
    mock_http_client.get.return_value = response

    with pytest.raises(KeyError):
        await gc_client.get_coords("350 5th Ave")
