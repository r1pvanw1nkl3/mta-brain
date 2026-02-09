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

        self.state_store.set_kv(
            Keys.trip(trip_key), trip_data, config.trip_metadata_ttl
        )

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
            current_time
            - 300,  # keep some old arrivals for matching, in case trains come early
            config.redis_gtfs_ttl,
        )


class StopReader:
    def __init__(self, state_store: StateStore, static_store: StaticStore):
        self.state_store = state_store
        self.static_store = static_store

    def get_arrivals_board(
        self, stop_id: str, lookahead_min: int = 60
    ) -> list[md.Arrival]:
        if stop_id.endswith(("N", "S")):
            base_stop_id = stop_id[:-1]
            platforms = [stop_id]
        else:
            base_stop_id = stop_id
            platforms = [stop_id + "N", stop_id + "S"]

        live_entries = []
        for p_id in platforms:
            direction = p_id[-1]
            zset_data = self.state_store.get_zset(
                Keys.arrivals(p_id), int(time.time() + (lookahead_min * 60))
            )
            for tid, ts in zset_data.items():
                live_entries.append((tid, ts, direction))

        scheduled_data = self.static_store.get_scheduled_arrivals(
            base_stop_id, lookahead_min
        )

        # 2. Group Schedule by Route and Direction for fast fuzzy lookup
        scheduled_groups = {}
        for s in scheduled_data:
            key = (s["route_id"], s["direction"])
            if key not in scheduled_groups:
                scheduled_groups[key] = []
            scheduled_groups[key].append(s)

        unified_board = []
        matched_static_ids = set()

        # 3. Process Live Data
        for trip_id, arrival_ts, dir_letter in live_entries:
            best_match = None

            # 1. Try EXACT ID match globally first (resilient to missing Redis metadata)
            # We try exact match first, then suffix match for prefixed static IDs
            for s in scheduled_data:
                if s["trip_id"] not in matched_static_ids:
                    if s["trip_id"] == trip_id or s["trip_id"].endswith("_" + trip_id):
                        best_match = s
                        break

            # 2. If no exact match, try to get route_id to enable fuzzy matching
            route_id = "???"
            raw_metadata = self.state_store.get_kv(Keys.trip(trip_id))
            if raw_metadata:
                live_update = md.TripUpdate.model_validate_json(raw_metadata)
                route_id = live_update.trip.route_id

            # 3. If metadata is missing, try to infer route from trip_id
            # (e.g., 081300_B..S66R -> B)
            if route_id == "???" and "_" in trip_id:
                parts = trip_id.split("_")
                if len(parts) > 1 and "." in parts[1]:
                    route_id = parts[1].split(".")[0]

            # 4. Try FUZZY match: Look for the closest scheduled train in the rt group
            if not best_match and route_id != "???":
                group_key = (route_id, dir_letter)
                candidates = scheduled_groups.get(group_key, [])
                min_diff = 900  # 15-minute window
                for cand in candidates:
                    if cand["trip_id"] in matched_static_ids:
                        continue
                    diff = abs(cand["arrival_timestamp"] - arrival_ts)
                    if diff < min_diff:
                        min_diff = diff
                        best_match = cand

            if best_match:
                matched_static_ids.add(best_match["trip_id"])
                unified_board.append(
                    md.Arrival(
                        trip_id=trip_id,
                        route_id=best_match["route_id"],
                        headsign=best_match["trip_headsign"],
                        direction=dir_letter,
                        arrival_time=int(arrival_ts),
                        is_realtime=True,
                        status="LIVE",
                    )
                )
            else:
                # Improve destination for LIVE-ADDED trains
                headsign = "In Transit"
                raw_metadata = self.state_store.get_kv(Keys.trip(trip_id))
                if raw_metadata:
                    live_update = md.TripUpdate.model_validate_json(raw_metadata)
                    if live_update.stop_time_update:
                        dest_stop_id = live_update.stop_time_update[-1].stop_id
                        headsign = self.static_store.get_stop_name(dest_stop_id)

                # If still "???", try a deep look in static DB for route/headsign
                if route_id == "???" or headsign == "In Transit":
                    static_meta = self.static_store.get_trip_metadata(trip_id)
                    if not static_meta:
                        # Try searching with suffix if we have a guess at the format
                        static_meta = self.static_store.get_trip_metadata("%" + trip_id)

                    if static_meta:
                        if route_id == "???":
                            route_id = static_meta["route_id"]
                        if headsign == "In Transit":
                            headsign = static_meta["trip_headsign"]

                unified_board.append(
                    md.Arrival(
                        trip_id=trip_id,
                        route_id=route_id,
                        headsign=headsign,
                        direction=dir_letter,
                        arrival_time=int(arrival_ts),
                        is_realtime=True,
                        status="LIVE-ADDED",
                    )
                )

        # 4. Add remaining Scheduled trips (The true "Ghosts")
        now_ts = int(time.time())
        for s in scheduled_data:
            if s["trip_id"] not in matched_static_ids:
                # If a specific platform was requested, only show that direction
                if stop_id.endswith(("N", "S")) and s["direction"] != stop_id[-1]:
                    continue

                # Drop trains that should have passed > 5 mins ago
                if s["arrival_timestamp"] < (now_ts - 300):
                    continue

                unified_board.append(
                    md.Arrival(
                        trip_id=s["trip_id"],
                        route_id=s["route_id"],
                        headsign=s["trip_headsign"],
                        direction=s["direction"],
                        arrival_time=s["arrival_timestamp"],
                        is_realtime=False,
                        status="SCHEDULED",
                    )
                )
        final_board = [
            train
            for train in unified_board
            if train.arrival_time
            >= (now_ts - 60)  # Allow 60s of "recently passed" for UX
        ]

        return sorted(final_board, key=lambda x: x.arrival_time)
