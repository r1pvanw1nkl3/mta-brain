from enum import IntEnum
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# Domain Models


class Arrival(BaseModel):
    trip_id: str
    arrival_time: int
    route_id: str
    headsign: str
    direction: str
    is_realtime: bool
    status: str


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
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4
    UNKNOWN = 0


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


class MtaTripDescriptor(BaseModel):
    train_id: Optional[str] = Field(None, alias="train_id")
    is_assigned: Optional[bool] = Field(None, alias="is_assigned")
    direction: Optional[Direction] = Field(Direction.NORTH, alias="direction")


class Trip(BaseModel):
    trip_id: str
    start_date: int
    start_time: Optional[str] = None
    schedule_relationship: Optional[TripScheduleRelationship] = None
    route_id: str
    direction_id: Optional[Direction] = None
    mta_trip_ext: Optional[MtaTripDescriptor] = Field(
        None,
        validation_alias=AliasChoices("nyct_trip_descriptor", "[nyct_trip_descriptor]"),
    )


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
