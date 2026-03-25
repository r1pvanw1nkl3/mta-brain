import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


def _get_clock_time(time: int) -> str:
    dt = datetime.fromtimestamp(time, tz=ZoneInfo("America/New_York"))
    return dt.strftime("%I:%M %p").lstrip("0")


class ArrivalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trip_id: str
    route_id: str
    direction: str
    arrival_time: int
    status: str
    headsign: str

    @computed_field
    def minutes_away(self) -> int:
        now = int(time.time())
        diff = self.arrival_time - now
        return max(0, diff // 60)

    @computed_field
    def clock_time(self) -> str:
        return _get_clock_time(self.arrival_time)


class NearbyArrivalsBoardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    gtfs_stop_id: str
    stop_name: str
    arrivals: list[ArrivalResponse]
    walk_time: float


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    stop_id: str = Field(exclude=True)
    arrival_time: int = Field(exclude=True)
    stop_name: str
    departure_time: int = Field(exclude=True)

    @computed_field
    def arrival(self) -> str:
        return _get_clock_time(self.arrival_time)

    @computed_field
    def departure(self) -> str:
        return _get_clock_time(self.departure_time)


class NearbyStopsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    stop_name: str
    gtfs_stop_id: str
    line: str
    lat: float
    lon: float
    dist_meters: float

    @model_validator(mode="before")
    @classmethod
    def extract_coords(cls, data: Any) -> Any:
        if hasattr(data, "coordinates"):
            data_dict = {
                "stop_name": data.stop_name,
                "gtfs_stop_id": data.gtfs_stop_id,
                "line": data.line,
                "lat": data.coordinates.lat,
                "lon": data.coordinates.lon,
                "dist_meters": data.dist_meters,
            }
            return data_dict
        if isinstance(data, dict) and "coordinates" in data:
            coords = data.get("coordinates", {})
            data["lat"] = coords.get("lat")
            data["lon"] = coords.get("lon")


class StopSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stop_id: str
    stop_name: str
    routes: str
    rank: int
