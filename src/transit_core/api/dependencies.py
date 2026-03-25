from fastapi import Request

from transit_core.core.engines.planner import PlannerEngine
from transit_core.core.repository import StopReader, TripReader


def get_stop_reader(request: Request) -> StopReader:
    return request.app.state.stop_reader


def get_trip_reader(request: Request) -> TripReader:
    return request.app.state.trip_reader


def get_planner_engine(request: Request) -> PlannerEngine:
    return request.app.state.planner_engine
