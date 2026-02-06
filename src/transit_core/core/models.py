from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Static GTFS Models


class StationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stop_id: str
    stop_name: str


class Station(StationSummary):
    lat: float = Field(validation_alias="stop_lat")
    lon: float = Field(validation_alias="stop_lon")
    parent_station: Optional[str]


# State Models


class StopDepartureBoard(BaseModel):
    stop_id: str
    departures: dict[str, int]


# GTFS models


class TripScheduleRelationship(IntEnum):
    SCHEDULED = 0
    ADDED = 1
    UNSCHEDULED = 2
    CANCELED = 3


class Direction(IntEnum):
    NORTH = 0
    SOUTH = 3


class TimeUpdate(BaseModel):
    delay: Optional[int] = None
    time: int
    uncertainty: Optional[int] = None


class StopTimeUpdate(BaseModel):
    stop_sequence: Optional[int] = None
    stop_id: str
    schedule_relationship: TripScheduleRelationship = TripScheduleRelationship.SCHEDULED
    arrival_time: Optional[TimeUpdate] = Field(None, alias="arrival")
    departure_time: Optional[TimeUpdate] = Field(None, alias="departure")


class Trip(BaseModel):
    trip_id: str
    start_date: int
    schedule_relationship: Optional[TripScheduleRelationship] = None
    route_id: str
    direction_id: Optional[Direction] = None


class Vehicle(BaseModel):
    trip: Trip
    current_stop_sequence: Optional[int] = None
    current_status: Optional[int] = None
    timestamp: str
    stop_id: str


class TripUpdate(BaseModel):
    trip: Trip
    stop_time_update: Optional[list[StopTimeUpdate]] = None


class Entity(BaseModel):
    id: str
    is_deleted: bool = False
    timestamp: Optional[str] = None
    trip_update: Optional[TripUpdate] = None
    vehicle: Optional[Vehicle] = None


class Feed(BaseModel):
    header: dict
    entity: list[Entity]
