import time

from transit_core.core.models import ArrivalsBoard
from transit_core.messenger.views import Section, Table


def _minutes_until(arrival_epoch: int, now: int) -> str:
    mins = max(0, round((arrival_epoch - now) / 60))
    return "now" if mins == 0 else f"{mins} min"


def present_arrivals_board(
    arrivals_board: ArrivalsBoard, now: int | None = None
) -> Section:
    subtitle = f"Arrivals for {arrivals_board.stop_name}"

    if not arrivals_board.arrivals:
        return Section("Arrivals", subtitle, "No upcoming arrivals.")

    now = now if now is not None else int(time.time())

    rows = [
        [
            a.route_id,
            a.direction,
            a.headsign or "",
            _minutes_until(a.arrival_time, now),
        ]
        for a in arrivals_board.arrivals
    ]

    table = Table(["Route", "Direction", "Destination", "ETA"], rows)
    return Section("Arrivals", subtitle, table)
