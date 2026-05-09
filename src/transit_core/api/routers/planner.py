from fastapi import APIRouter, Depends, HTTPException

from transit_core.api import schemas
from transit_core.api.dependencies import get_planner_engine
from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.models import Coordinates

router = APIRouter()


@router.get("/planner/nearby", response_model=list[schemas.ArrivalsBoardResponse])
async def get_nearby_arrivals(
    lat: float,
    lon: float,
    max_walk_time: int,
    planner: PlannerEngine = Depends(get_planner_engine),
):
    boards = await planner.get_nearby_arrivals(
        Coordinates(lat=lat, lon=lon), max_walk_time
    )

    if not boards:
        raise HTTPException(
            status_code=404,
            detail="No stops within range found for provided coordinates.",
        )
    return boards
