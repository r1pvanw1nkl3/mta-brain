from fastapi import APIRouter, Depends

from transit_core.api import schemas
from transit_core.api.dependencies import get_stop_reader
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


@router.get("/stops/search/")
async def stop_search(
    search_string: str, reader: StopReader = Depends(get_stop_reader)
):
    result = reader.fuzzy_station_search(search_string)
    return result
