import logging

import transit_core.core.models as md
from transit_core.config import get_settings
from transit_core.core.interfaces import StateStore

logger = logging.getLogger(__name__)

config = get_settings()


class Keys:
    @staticmethod
    def trip(trip_id: str) -> str:
        return f"trip:{trip_id}"

    @staticmethod
    def departures(stop_id: str) -> str:
        return f"departures:{stop_id}"

    @staticmethod
    def feed(feed_key: str) -> str:
        return f"feed:{feed_key}"


class TripRepository:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    def update_trip_status(self, trip_update: md.TripUpdate) -> None:
        trip_data = trip_update.model_dump_json()
        trip_key = trip_update.trip.trip_id

        self.state_store.set_kv(Keys.trip(trip_key), trip_data, config.redis_gtfs_ttl)

    def get_trip_status(self, trip_id: str) -> md.TripUpdate | None:
        json = self.state_store.get_kv(Keys.trip(trip_id))
        if not json:
            return None
        else:
            return md.TripUpdate.model_validate_json(json)


class StopRepository:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    def update_departures_board(self, board: md.StopDepartureBoard):
        self.state_store.sync_set(
            Keys.departures(board.stop_id), board.departures, config.redis_gtfs_ttl
        )

    def get_departures_board(self, stop_id: str) -> md.StopDepartureBoard | None:
        stops = self.state_store.get_zset(Keys.departures(stop_id))
        if not stops:
            return None
        return md.StopDepartureBoard(stop_id=stop_id, departures=stops)
