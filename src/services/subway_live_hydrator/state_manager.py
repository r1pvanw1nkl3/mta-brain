import logging
import time

import transit_core.core.models as md
from transit_core.core.repository import StopRepository, TripRepository

logger = logging.getLogger(__name__)


def hydrate_realtime_data(
    feed: md.Feed, trip_repo: TripRepository, stop_repo: StopRepository
) -> None:
    state_store = trip_repo.state_store

    departures_boards: dict[str, dict[str, int]] = {}
    trip_updates_count = 0

    with state_store.batch_session():
        current_time = int(time.time())
        for entity in feed.entity:
            if entity.trip_update is not None:
                trip_updates_count += 1
                trip_update = entity.trip_update
                trip_repo.update_trip_status(trip_update)
                trip_id = trip_update.trip.trip_id
                if trip_update.stop_time_update:
                    for stop_time in trip_update.stop_time_update:
                        if stop_time.arrival_time:
                            board_time = stop_time.arrival_time.time
                        elif stop_time.departure_time:
                            board_time = stop_time.departure_time.time
                        else:
                            continue
                        if board_time < current_time:
                            continue
                        stop_id = stop_time.stop_id
                        if stop_id not in departures_boards:
                            departures_boards[stop_id] = {}
                        departures_boards[stop_id][trip_id] = board_time
        for stop_id, departures in departures_boards.items():
            board = md.StopDepartureBoard(stop_id=stop_id, departures=departures)
            stop_repo.update_departures_board(board, current_time)

    logger.debug(
        "Hydration completed",
        extra={
            "trip_updates_processed": trip_updates_count,
            "stops_updated": len(departures_boards),
        },
    )
