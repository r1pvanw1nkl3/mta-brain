from fastapi import APIRouter, Depends

from transit_core.api import schemas
from transit_core.api.dependencies import get_stop_reader
from transit_core.api.schemas import StopSearchResponse
from transit_core.core.models import Coordinates
from transit_core.core.repository import StopReader

router = APIRouter()


@router.get("/stops/{stop_id}/arrivals", response_model=list[schemas.ArrivalResponse])
async def get_arrivals(
    stop_id: str, live: bool = False, reader: StopReader = Depends(get_stop_reader)
):
    if live:
        arrivals = reader.get_arrivals_board(stop_id, get_schedules=False)
    else:
        arrivals = reader.get_arrivals_board(stop_id)

    return arrivals


@router.get("/stops/search", response_model=list[StopSearchResponse])
async def stop_search(
    search_string: str, reader: StopReader = Depends(get_stop_reader)
):
    result = reader.fuzzy_station_search(search_string)
    return [schemas.StopSearchResponse.model_validate(row) for row in result]


@router.get("/stops/search/coords", response_model=list[schemas.NearbyStopsResponse])
async def get_nearby_stops(
    lat: float,
    lon: float,
    count: int,
    reader: StopReader = Depends(get_stop_reader),
):
    result = reader.get_nearby_stops(Coordinates(lat=lat, lon=lon), count)

    return [schemas.NearbyStopsResponse.model_validate(row) for row in result]
