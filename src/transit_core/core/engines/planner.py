from transit_core.core.interfaces import StreetRoutingService
from transit_core.core.models import ArrivalsBoard, Coordinates
from transit_core.core.repository import StopReader


class PlannerEngine:
    def __init__(self, stop_reader: StopReader, routing_service: StreetRoutingService):
        self.stop_reader = stop_reader
        self.routing_service = routing_service

    async def get_nearby_arrivals(
        self, location: Coordinates, max_walk_time_mins: int = 25
    ) -> list[ArrivalsBoard]:
        # 1. Get 25 nearby stops. Imagine needing more? That's the dream.
        nearby_stops = {
            stop.gtfs_stop_id: stop
            for stop in self.stop_reader.get_nearby_stops(location, 25)
        }

        # 2. Build our parameter and call OSRM
        stop_coords_dict = {stop.id: stop.coordinates for stop in nearby_stops.values()}

        distances = await self.routing_service.get_walk_times(
            user_location=location, stop_locations=stop_coords_dict
        )

        # 3. Go through the stops and check that the walk time is within max walk time
        stops_within_range: dict[str, float] = {}

        for stop in nearby_stops.values():
            if (
                walk_time_seconds := distances.get(stop.id)
            ) is not None and walk_time_seconds <= (max_walk_time_mins * 60):
                stops_within_range[stop.gtfs_stop_id] = walk_time_seconds / 60

        # 4. Build our output model, sort, return

        arrivals_boards: list[ArrivalsBoard] = []

        for gtfs_stop_id, walk_time_minutes in stops_within_range.items():
            board = self.stop_reader.get_arrivals_board(
                stop_id=gtfs_stop_id, get_schedules=False
            )

            board.walk_time = walk_time_minutes

            arrivals_boards.append(board)

        arrivals_boards.sort(key=lambda x: x.walk_time)

        return arrivals_boards
