import time
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


def _get_clock_time(time: int) -> str:
    dt = datetime.fromtimestamp(time)
    return dt.strftime("%I:%M %p").lstrip("0")


class ArrivalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trip_id: str
    route_id: str
    direction: str
    arrival_time: int
    status: str

    @computed_field
    def minutes_away(self) -> int:
        now = int(time.time())
        diff = self.arrival_time - now
        return max(0, diff // 60)

    @computed_field
    def clock_time(self) -> str:
        return _get_clock_time(self.arrival_time)


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
