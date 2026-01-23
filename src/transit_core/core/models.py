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
    delay: int
    time: int
    uncertainty: int


class StopTimeUpdate(BaseModel):
    stop_sequence: int
    stop_id: str
    schedule_relationship: TripScheduleRelationship = TripScheduleRelationship.SCHEDULED
    arrival_time: Optional[TimeUpdate] = Field(None, alias="arrival")
    departure_time: Optional[TimeUpdate] = Field(None, alias="departure")


class Trip(BaseModel):
    trip_id: str
    start_date: int
    schedule_relationship: TripScheduleRelationship
    route_id: str
    direction_id: Direction


class Vehicle(BaseModel):
    trip: Trip
    id: int
    current_stop_sequence: int
    current_status: str
    timestamp: str
    stop_id: str
