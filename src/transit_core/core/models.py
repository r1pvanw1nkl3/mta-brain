from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stop_id: str
    stop_name: str


class Station(StationSummary):
    lat: float = Field(validation_alias="stop_lat")
    lon: float = Field(validation_alias="stop_lon")
    parent_station: Optional[str]
