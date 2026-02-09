import logging
import time

import transit_core.core.models as md
from transit_core.config import get_settings
from transit_core.core.interfaces import StateStore, StaticStore

logger = logging.getLogger(__name__)

config = get_settings()


class Keys:
    @staticmethod
    def trip(trip_id: str) -> str:
        return f"trip:{trip_id}"

    @staticmethod
    def arrivals(stop_id: str) -> str:
        return f"arrivals:{stop_id}"

    @staticmethod
    def feed(feed_key: str) -> str:
        return f"feed:{feed_key}"


class TripWriter:
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


class TripReader:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    def get_trip_status(self, trip_id: str) -> md.TripUpdate | None:
        json = self.state_store.get_kv(Keys.trip(trip_id))
        if not json:
            return None
        else:
            return md.TripUpdate.model_validate_json(json)


class StopWriter:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    def update_arrivals_board(self, stop_id, board: dict[str, int], current_time: int):
        self.state_store.sync_set(
            Keys.arrivals(stop_id),
            board,
            current_time,
            config.redis_gtfs_ttl,
        )


class StopReader:
    def __init__(self, state_store: StateStore, static_store: StaticStore):
        self.state_store = state_store
        self.static_store = static_store

    def get_arrivals_board(self, stop_id: str, lookahead_min: int = 60):
        # 1. Fetch data from both sources
        # Use union (|) to combine N and S sets from Redis
        live_data = self.state_store.get_zset(
            Keys.arrivals(stop_id + "N")
        ) | self.state_store.get_zset(Keys.arrivals(stop_id + "S"))

        scheduled_data = self.static_store.get_scheduled_arrivals(
            stop_id, lookahead_min
        )

        unified_board = []
        matched_static_ids = set()

        # 2. Process Live Data first
        for live_id, arrival_ts in live_data.items():
            # Clean ID: 20260208_103800_C..N -> 103800_C..N
            clean_id = live_id.split("_", 1)[-1] if "_" in live_id else live_id

            # Route Extraction: 103800_C..N -> C
            # Most MTA IDs have the route between the underscores or before the dots
            # This regex-free approach is usually safe for ACE/BDFM
            live_route = clean_id.split(".")[0].split("_")[-1]

            # Find the match in the static schedule
            static_match = next(
                (s for s in scheduled_data if clean_id in s["trip_id"]), None
            )

            if static_match:
                matched_static_ids.add(static_match["trip_id"])
                unified_board.append(
                    md.Arrival(
                        trip_id=live_id,
                        route_id=static_match["route_id"],
                        headsign=static_match["trip_headsign"],
                        arrival_time=arrival_ts,
                        is_realtime=True,
                        status="LIVE",
                    )
                )
            else:
                # This is a train that is NOT in the static schedule for this window
                unified_board.append(
                    md.Arrival(
                        trip_id=live_id,
                        route_id=live_route,
                        headsign="In Transit",
                        arrival_time=arrival_ts,
                        is_realtime=True,
                        status="LIVE-ADDED",
                    )
                )

        # 3. Process remaining Scheduled Data (The "Ghosts")
        for sched in scheduled_data:
            # If this specific static ID was already 'claimed' by a live train, skip it
            if sched["trip_id"] in matched_static_ids:
                continue

            if sched["arrival_timestamp"] < (int(time.time()) - 300):
                continue

            unified_board.append(
                md.Arrival(
                    trip_id=sched["trip_id"],
                    route_id=sched["route_id"],
                    headsign=sched["trip_headsign"],
                    arrival_time=sched["arrival_timestamp"],
                    is_realtime=False,
                    status="SCHEDULED",
                )
            )

        return sorted(unified_board, key=lambda x: x.arrival_time)
