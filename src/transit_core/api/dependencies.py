from fastapi import Request

from transit_core.core.repository import StopReader, TripReader


def get_stop_reader(request: Request) -> StopReader:
    return StopReader(request.app.state.state_store, request.app.state.static_store)


def get_trip_reader(request: Request) -> TripReader:
    return TripReader(request.app.state.state_store, request.app.state.static_store)
