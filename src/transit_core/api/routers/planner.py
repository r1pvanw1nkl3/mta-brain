from fastapi import APIRouter, Depends, HTTPException

from transit_core.api import schemas
from transit_core.api.dependencies import get_trip_reader
from transit_core.core.repository import TripReader

router = APIRouter()


@router.get("/planner", response_model=list[schemas.TripResponse])
async def get_arrivals(trip_id: str, reader: TripReader = Depends(get_trip_reader)):
    results = reader.get_trip_arrivals(trip_id)
    if not results:
        raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found")

    return results
