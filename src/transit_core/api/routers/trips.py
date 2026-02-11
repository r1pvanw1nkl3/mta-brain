from fastapi import APIRouter, Depends, HTTPException

from transit_core.api import schemas
from transit_core.api.dependencies import get_trip_reader
from transit_core.core.repository import TripReader

router = APIRouter()


@router.get("/trips/{trip_id}/arrivals", response_model=list[schemas.TripResponse])
async def get_arrivals(trip_id: str, reader: TripReader = Depends(get_trip_reader)):
    results = reader.get_trip_arrivals(trip_id)
    if not results:
        raise HTTPException(status_code=404, detail=f"Trip {trip_id} not found")

    return results


@router.get("/trips/{trip_id}/status")
async def get_status(trip_id: str, reader: TripReader = Depends(get_trip_reader)):
    return reader.get_trip_status(trip_id)
