from pydantic import BaseModel, ConfigDict


class Station(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stop_id: str
    stop_name: str
    lat: float
    lon: float
    parent_station: str